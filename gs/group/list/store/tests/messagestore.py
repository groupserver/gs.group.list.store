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
from mock import (MagicMock)
from unittest import TestCase
from gs.group.list.base.emailmessage import EmailMessage
from gs.group.list.store.messagestore import EmailMessageStore


class EmailMessageStoreTest(TestCase):
    m = '''From: Me <a.member@example.com>
To: Group <group@groups.example.com>
Subject: Violence

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
