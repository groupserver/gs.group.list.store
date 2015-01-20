# -*- coding: utf-8 -*-
############################################################################
#
# Copyright © 2015 OnlineGroups.net and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
############################################################################
from __future__ import absolute_import, unicode_literals
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mock import (MagicMock, patch)
from unittest import TestCase
from gs.group.list.base.emailmessage import EmailMessage
import gs.group.list.store.messagestore  # lint:ok
from gs.group.list.store.messagestore import (EmailMessageStore)


class EmailMessageStoreTest(TestCase):
    m = '''From: Me <a.member@example.com>
Subject: Violence
To: Group <group@groups.example.com>

Tonight on Ethel the Frog we look at violence.\n'''

    def setUp(self):
        self.message = EmailMessage(self.m, list_title='Ethel the Frog',
                                    group_id='ethel')
        context = MagicMock()
        self.messageStore = EmailMessageStore.from_email_message(
            context, self.message)

    def test_in_reply_to(self):
        'Test the In-Reply-To header when it is unset'
        r = self.messageStore.inreplyto
        self.assertEqual('', r)

    def test_in_reply_to_set(self):
        e = 'person@example.com'
        self.messageStore.message['In-reply-to'] = e
        r = self.messageStore.inreplyto
        self.assertEqual(e, r)

    def test_attachment_count(self):
        'Check that the text-body does not count as an attachment'
        r = self.messageStore.attachment_count
        self.assertEqual(0, r)

    def get_txt_html_msg(self):
        retval = MIMEMultipart()
        a = MIMEMultipart('alternative')
        retval.attach(a)
        tt = MIMEText(
            'Tonight on Ethel the Frog\u2026 we look at violence.\n',
            'plain', 'UTF-8')
        a .attach(tt)
        th = MIMEText(
            '<p>Tonight on Ethel the Frog&#8230; we look at '
            'violence.\n</p>', 'html', 'us-ascii')
        a.attach(th)

        for h, v in self.messageStore.message.items():
            retval.add_header(h, v)
        return retval

    def test_attachment_count_html_body(self):
        self.messageStore.message = self.get_txt_html_msg()
        r = self.messageStore.attachment_count
        self.assertEqual(0, r)

    def test_attachment_count_file(self):
        'Can we see one file'
        m = self.get_txt_html_msg()
        textFile = MIMEText('The violence of British Gangland.')
        textFile.add_header('Content-Disposition', 'attachment',
                            filename='gangland.txt')
        m.attach(textFile)
        self.messageStore.message = m

        r = self.messageStore.attachment_count
        self.assertEqual(1, r)

    def test_attachment_count_files(self):
        'Can we see multiple files'
        m = self.get_txt_html_msg()
        textFile = MIMEText('The violence of British Gangland.')
        textFile.add_header('Content-Disposition', 'attachment',
                            filename='gangland.txt')
        m.attach(textFile)
        textFile = MIMEText('When he grew up he took to putting the boot '
                            'in.')
        textFile.add_header('Content-Disposition', 'attachment',
                            filename='durk.txt')
        m.attach(textFile)
        self.messageStore.message = m

        r = self.messageStore.attachment_count
        self.assertEqual(2, r)

    @staticmethod
    def get_attachment(payload='', fileId='', filename='', length=0,
                       md5_sum='', encoding='utf-8', mimetype='text/plain',
                       cid=''):
        maintype, subtype = mimetype.split('/')
        retval = {
            'payload': payload,
            'fileid': fileId,
            'filename': filename,
            'length': length,
            'md5': md5_sum,
            'charset': encoding,
            'maintype': maintype,
            'subtype':  subtype,
            'mimetype': mimetype,
            'contentid': cid}
        return retval

    @patch('gs.group.list.store.messagestore.log')
    def test_store_attachment_text_body(self, l):
        'Ensure we do not store anything that looks like the text body'
        p = 'Tonight on Ethel the Frog\u2026 we look at violence.\n'
        a = self.get_attachment(payload=p.encode('utf-8'), length=len(p))

        with patch.object(self.messageStore, 'add_file') as addFileMock:
            self.messageStore.store_attachment(a)
        self.assertEqual(0, addFileMock.call_count)

    @patch('gs.group.list.store.messagestore.log')
    def test_store_attachment_html_body(self, l):
        'Ensure we do not store anything that looks like the HTML body'
        p = '<p>Tonight on Ethel the Frog&#8230; we look at violence.</p>'
        a = self.get_attachment(payload=p.encode('ascii'), length=len(p),
                                mimetype='text/html')

        with patch.object(self.messageStore, 'add_file') as addFileMock:
            self.messageStore.store_attachment(a)
        self.assertEqual(0, addFileMock.call_count)

    @patch('gs.group.list.store.messagestore.log')
    def test_store_attachment_cid_only(self, l):
        '''Ensure we do not store anything that looks like a file that is
just used in the HTML body'''
        p = b'This is not an image'
        a = self.get_attachment(payload=p, length=len(p),
                                mimetype='image/jpeg', cid='something')

        with patch.object(self.messageStore, 'add_file') as addFileMock:
            self.messageStore.store_attachment(a)
        self.assertEqual(0, addFileMock.call_count)

    @patch('gs.group.list.store.messagestore.log')
    def test_store_attachment_cid(self, l):
        p = b'This is not an image'
        a = self.get_attachment(payload=p, length=len(p),
                                mimetype='image/jpeg', cid='something',
                                filename="foo.jpg")

        with patch.object(self.messageStore, 'add_file') as addFileMock:
            self.messageStore.store_attachment(a)
        self.assertEqual(1, addFileMock.call_count)

    @patch('gs.group.list.store.messagestore.log')
    def test_store_attachment_empty(self, l):
        p = b''
        a = self.get_attachment(payload=p, length=len(p),
                                mimetype='image/jpeg', filename="foo.jpg")

        with patch.object(self.messageStore, 'add_file') as addFileMock:
            self.messageStore.store_attachment(a)
        self.assertEqual(0, addFileMock.call_count)

    @patch('gs.group.list.store.messagestore.log')
    def test_store_attachment(self, l):
        '''Ensure we do not store anything that looks like a file that is
used in the HTML body'''
        p = b'This is not an image'
        a = self.get_attachment(payload=p, length=len(p),
                                mimetype='image/jpeg',
                                filename="foo.jpg")

        with patch.object(self.messageStore, 'add_file') as addFileMock:
            self.messageStore.store_attachment(a)
        self.assertEqual(1, addFileMock.call_count)
