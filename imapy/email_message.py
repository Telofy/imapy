# -*- coding: utf-8 -*-
"""
    imapy.email_message
    ~~~~~~~~~~~~~~~~~~~

    This module contains EmailMessage class used for parsing email messages
    and passing calls which modify email state to imapy.IMAP() class.

    :copyright: (c) 2015 by Vladimir Goncharov.
    :license: MIT, see LICENSE for more details.
"""

import re
import six
from encodings import search_function as find_codec
from email.header import decode_header
from bs4.dammit import EncodingDetector
from . import utils
from .structures import CaseInsensitiveDict
from .exceptions import (
    EmailParsingError,
)


class EmailMessage(CaseInsensitiveDict):
    """Class for parsing email message"""

    def __init__(self, **kwargs):
        super(EmailMessage, self).__init__()
        # inject connections
        self.uid = kwargs.pop('uid', None)
        self.folder = kwargs.pop('folder', None)
        self.email_obj = kwargs.pop('email_obj', None)
        self.imap_obj = kwargs.pop('imap_obj', None)
        # init
        self.update(kwargs)
        self['to'] = []
        self['subject'] = ''
        self['cc'] = []
        self['text'] = []
        self['html'] = []
        self['headers'] = CaseInsensitiveDict()
        self['flags'] = kwargs.pop('flags', None)
        self['attachments'] = []
        self.parse()

    def clean_value(self, value, encoding, fallback='utf-8'):
        """Converts value to utf-8 encoding"""
        if isinstance(value, six.text_type):
            # Already Unicode
            return value
        encoding = encoding if encoding and find_codec(encoding) else fallback
        return value.decode(encoding, errors='replace')

    def _normalize_string(self, text):
        '''Removes excessive spaces, tabs, newlines, etc.'''
        conversion = {
            # newlines
            '\r\n\t': ' ',
            # replace excessive empty spaces
            '\s+': ' '
        }
        for find, replace in six.iteritems(conversion):
            text = re.sub(find, replace, text, re.UNICODE)
        return text

    def _get_links(self, text):
        links = []
        """Returns list of found links in text"""
        matches = re.findall(
            '(?<=[\s^\<])(?P<link>https?\:\/\/.*?)(?=[\s\>$])', text, re.I)
        if(matches):
            for match in matches:
                links.append(match)

        return list(set(links))

    def mark(self, flags):
        """Alias function for imapy.mark()"""
        if not isinstance(flags, list):
            flags = [flags]
        # update self['flags']
        for t in flags:
            if t[:2] == 'un':
                if t[2:] in self['flags']:
                    self['flags'].remove(t[2:])
            else:
                if t not in self['flags']:
                    self['flags'].append(t)

        return self.imap_obj.mark(flags, self.uid)

    def delete(self):
        """Alias function for imapy.delete_message"""
        return self.imap_obj.delete_message(self.uid, self.folder)

    def copy(self, new_mailbox):
        """Alias function for imapy.copy_message"""
        return self.imap_obj.copy_message(self.uid, new_mailbox, self)

    def move(self, new_mailbox):
        """Alias function for imapy.copy_message"""
        return self.imap_obj.move_message(self.uid, new_mailbox, self)

    def parse(self):
        """Parses email object and stores data so that email parts can be
        access with a dictionary syntax like msg['from'], msg['to']
        """
        fallback_encoding = 'utf-8'
        # check main body
        if not self.email_obj.is_multipart():
            charset = self.email_obj.get_content_charset() \
                or self.email_obj.get_charset()
            charset = charset if charset and find_codec(charset) else fallback_encoding
            text = self.email_obj.get_payload(decode=True).decode(charset, errors='replace')
            self['text'].append(
                {
                    'text': text,
                    'text_normalized': self._normalize_string(text),
                    'links': self._get_links(text)
                }
            )
        # check attachments
        else:
            for part in self.email_obj.walk():
                # multipart/* are just containers
                if part.get_content_maintype() == 'multipart':
                    continue
                # Empty part, maybe a separator marking the end of the message
                if not part.keys():
                    continue
                content_type = part.get_content_type()
                charset = part.get_content_charset() \
                    or part.get_charset()
                if content_type == 'text/plain':
                    # Convert text
                    charset = charset if charset and find_codec(charset) else fallback_encoding
                    text = part.get_payload(decode=True).decode(charset, errors='replace')
                    self['text'].append(
                        {
                            'text': text,
                            'text_normalized': self._normalize_string(text),
                            'links': self._get_links(text)
                        }
                    )
                elif content_type == 'text/html':
                    # convert html
                    html = part.get_payload(decode=True)
                    if not charset:
                        charset = EncodingDetector \
                            .find_declared_encoding(html, is_html=True)
                    charset = charset if charset and find_codec(charset) else fallback_encoding
                    self['html'].append(html.decode(charset, errors='replace'))
                else:
                    try:
                        data = part.get_payload(decode=True)
                    # rare cases when we get decoding error
                    except AssertionError:
                        data = None
                    attachment_fname = decode_header(part.get_filename() or '')
                    filename = self.clean_value(
                        attachment_fname[0][0], attachment_fname[0][1]
                    )
                    attachment = {
                        'filename': filename,
                        'data': data,
                        'content_type': content_type
                    }
                    self['attachments'].append(attachment)

        # subject
        if 'subject' in self.email_obj:
            msg_subject = decode_header(self.email_obj['subject'])
            self['subject'] = self.clean_value(
                msg_subject[0][0], msg_subject[0][1])
        # from
        # cleanup header
        from_header_cleaned = re.sub('[\n\r\t]+', ' ', self.email_obj['from'])
        msg_from = decode_header(from_header_cleaned)
        msg_txt = ''
        for part in msg_from:
            msg_txt += self.clean_value(part[0], part[1])
        if '<' in msg_txt and '>' in msg_txt:
            result = re.match('(?P<from>.*)?(?P<email>\<.*\>)', msg_txt, re.U)
            self['from_whom'] = result.group('from').strip()
            self['from_email'] = result.group('email').strip('<>')
            self['from'] = msg_txt
        else:
            self['from_whom'] = ''
            self['from_email'] = self['from'] = msg_txt.strip()

        # to
        if 'to' in self.email_obj:
            msg_to = decode_header(self.email_obj['to'])
            self['to'] = self.clean_value(
                msg_to[0][0], msg_to[0][1]).strip('<>')

        # cc
        msg_cc = decode_header(str(self.email_obj['cc']))
        cc_clean = self.clean_value(msg_cc[0][0], msg_cc[0][1])
        if cc_clean and cc_clean.lower() != 'none':
            # split recepients
            recepients = cc_clean.split(',')
            for recepient in recepients:
                if '<' in recepient and '>' in recepient:
                    # (name)? + email
                    matches = re.findall('((?P<to>.*)?(?P<to_email>\<.*\>))',
                                         recepient, re.U)
                    if matches:
                        for match in matches:
                            self['cc'].append(
                                {
                                    'cc': match[0],
                                    'cc_to': match[1].strip(" \n\r\t"),
                                    'cc_email': match[2].strip("<>"),
                                }
                            )
                    else:
                        raise EmailParsingError(
                            "Error parsing CC message header. "
                            "Header value: {header}".format(header=cc_clean)
                        )
                else:
                    # email only
                    self['cc'].append(
                        {
                            'cc': recepient,
                            'cc_to': '',
                            'cc_email': recepient,
                        }
                    )

        # Date
        self['date'] = self.email_obj['Date']

        # message headers
        for header, val in self.email_obj.items():
            if header in self['headers']:
                self['headers'][header].append(val)
            else:
                self['headers'][header] = [val]
