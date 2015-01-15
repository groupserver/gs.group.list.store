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
from datetime import datetime
try:  # Python 2
    from hashlib import md5
    INT = long
except:  # Python 3
    from md5 import md5  # lint:ok
    INT = int
from logging import getLogger
log = getLogger('gs.group.list.store.messagestore')
import re
from zope.cachedescriptors.property import Lazy
from zope.datetime import parseDatetimetz
from gs.core import to_unicode_or_bust, convert_int2b62
from gs.group.list.base import EmailMessage
from Products.XWFCore.XWFUtils import removePathsFromFilenames
from .queries import (EmailMessageStorageQuery, FileMetadataStorageQuery)


class EmailMessageStore(EmailMessage):

    def __init__(self, context, message, list_title='', group_id='',
                 site_id='', sender_id_cb=None, replace_mail_date=True):
        super(EmailMessageStore, self).__init__(
            message, list_title, group_id, site_id, sender_id_cb)
        self.context = context
        self._list_title = list_title
        self.replace_mail_date = replace_mail_date

    @classmethod
    def from_email_message(cls, context, emailMessage,
                           replaceMailDate=True):
        retval = cls(emailMessage.message, emailMessage.list_title,
                     emailMessage.group_id, emailMessage.site_id,
                     emailMessage.sender_id_cb, replaceMailDate)
        return retval

    @Lazy
    def emailQuery(self):
        retval = EmailMessageStorageQuery(self)
        return retval

    @Lazy
    def fileQuery(self):
        retval = FileMetadataStorageQuery(self)
        return retval

    @staticmethod
    def calculate_file_id(file_body, mime_type):
        '''Generate a new identifer for a file
:param bytes file_body: The body of the file
:param string mime_type: The MIME-type of the file
:returns: A 3-tuple of ``(identifier, length, fileMD5)

Two files will have the same ID if

* They have the same MD5 Sum, *and*
* They have the same length, *and*
* They have the same MIME-type.'''
        length = len(file_body)
        md5_sum = md5()
        for c in file_body:
            md5_sum.update(c)
        file_md5 = md5_sum.hexdigest()
        md5_sum.update(':' + str(length) + ':' + mime_type)
        vNum = convert_int2b62(INT(md5_sum.hexdigest(), 16))
        retval = (to_unicode_or_bust(vNum), length, file_md5)
        return retval

    @Lazy
    def attachments(self):
        def split_multipart(msg, pl):
            if msg.is_multipart():
                for b in msg.get_payload():
                    pl = split_multipart(b, pl)
            else:
                pl.append(msg)

            return pl

        retval = []
        payload = self.message.get_payload()
        if isinstance(payload, list):
            outmessages = []
            for i in payload:
                outmessages = split_multipart(i, outmessages)

            for msg in outmessages:
                actual_payload = msg.get_payload(decode=True)
                encoding = msg.get_param('charset', self.encoding)
                pd = self.parse_disposition(msg.get('content-disposition',
                                                    ''))
                filename = to_unicode_or_bust(pd, encoding) if pd else ''
                fileid, length, md5_sum = self.calculate_file_id(
                    actual_payload, msg.get_content_type())
                retval.append({
                    'payload': actual_payload,
                    'fileid': fileid,
                    'filename': filename,
                    'length': length,
                    'md5': md5_sum,
                    'charset': encoding,  # --=mpj17=-- Issues?
                    'maintype': msg.get_content_maintype(),
                    'subtype': msg.get_content_subtype(),
                    'mimetype': msg.get_content_type(),
                    'contentid': msg.get('content-id', '')})
        else:
            # Since we aren't a bunch of attachments, actually decode the
            #   body
            payload = self.message.get_payload(decode=True)
            cd = self.message.get('content-disposition', '')
            pd = self.parse_disposition(cd)
            filename = to_unicode_or_bust(pd, self.encoding) if pd else ''

            fileid, length, md5_sum = self.calculate_file_id(
                payload, self.message.get_content_type())
            retval = [{
                      'payload': payload,
                      'md5': md5_sum,
                      'fileid': fileid,
                      'filename': filename,
                      'length': length,
                      'charset': self.message.get_charset(),
                      'maintype': self.message.get_content_maintype(),
                      'subtype': self.message.get_content_subtype(),
                      'mimetype': self.message.get_content_type(),
                      'contentid': self.message.get('content-id', '')}]
        assert retval is not None
        assert type(retval) == list
        return retval

    @Lazy
    def attachment_count(self):
        count = 0
        for item in self.attachments:
            if item['filename']:
                count += 1
        return count

    @Lazy
    def html_body(self):
        for item in self.attachments:
            if item['filename'] == '' and item['subtype'] == 'html':
                return to_unicode_or_bust(item['payload'], self.encoding)
        return ''

    @Lazy
    def date(self):
        retval = datetime.now()
        d = self.get('date', '').strip()
        if d and not self.replace_mail_date:
            # if we have the format Sat, 10 Mar 2007 22:47:20 +1300 (NZDT)
            # strip the (NZDT) bit before parsing, otherwise we break the
            # parser
            d = re.sub(' \(.*?\)', '', d)
            retval = parseDatetimetz(d)
        assert retval
        return retval

    def manage_addMail(self, msg):
        """ Store mail & attachments in a folder and return it."""
        ids = []
        for attachment in msg.attachments:
            if ((attachment['filename'] == '')
                    and (attachment['subtype'] == 'plain')):
                # We definately don't want to save the plain text body
                # again!
                pass
            elif ((attachment['filename'] == '')
                    and (attachment['subtype'] == 'html')):
                # We might want to do something with the HTML body some day,
                # but we archive the HTML body here, as it suggests in the
                # log message. The HTML body is archived along with the
                # plain text body.
                m = '%s (%s): archiving HTML message.' % \
                    (self.listTitle, self.group_id)
                log.info(m)
            elif attachment['contentid'] and (attachment['filename'] == ''):
                # TODO: What do we want to do with these? They are typically
                # part of an HTML message, for example the images, but what
                # should we do with them once we've stripped them?
                m = '%s (%s): stripped, but not archiving %s attachment '\
                    '%s; it appears to be part of an HTML message.' % \
                    (self.listTitle, self.group_id,
                     attachment['maintype'], attachment['filename'])
                log.info(m)
            elif attachment['length'] <= 0:
                # Empty attachment. Kinda pointless archiving this!
                m = '%s (%s): stripped, but not archiving %s attachment '\
                    '%s; attachment was of zero size.' % \
                    (self.listTitle, self.group_id,
                     attachment['maintype'], attachment['filename'])
                log.warn(m)
            else:
                m = '%s (%s): stripped and archiving %s attachment %s' %\
                    (self.listTitle, self.group_id,
                     attachment['maintype'], attachment['filename'])
                log.info(m)

                nid = self.addGSFile(attachment['filename'], msg.subject,
                                     msg.sender_id, attachment['payload'],
                                     attachment['mimetype'])
                ids.append(nid)

        self.emailQuery.insert()
        self.fileQuery.insert(self, ids)

        return (msg.post_id, ids)

    def addGSFile(self, title, topic, creator, data, content_type):
        """ Adds an attachment as a file.

        """
        # TODO: group ID should be more robust
        group_id = self.getId()
        storage = self.FileLibrary2.get_fileStorage()
        fileId = storage.add_file(data)
        fileObj = storage.get_file(fileId)
        fixedTitle = removePathsFromFilenames(title)
        fileObj.manage_changeProperties(
            content_type=content_type, title=fixedTitle,
            tags=['attachment'], group_ids=[group_id],
            dc_creator=creator, topic=topic)
        fileObj.reindex_file()
        #
        # Commit the ZODB transaction -- this basically makes it impossible
        # for us to rollback, but since our RDB transactions won't be rolled
        # back anyway, we do this so we don't have dangling metadata.
        #
        # --=mpj17=-- But it caused death on my local box. So I am
        # experimenting with commenting it out.
        # transaction.commit()
        return fileId


def group_store_factory(group, message):
    'For the ZCML, which really does not like class methods.'
    return EmailMessageStore.from_email_message(group, message)


def groupInfo_store_factory(groupInfo, message):
    'For the ZCML, which really does not like class methods.'
    return EmailMessageStore.from_email_message(groupInfo.groupObj, message)
