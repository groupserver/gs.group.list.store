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
from logging import getLogger
log = getLogger('gs.group.list.store.messagestore')
import re
from zope.cachedescriptors.property import Lazy
from zope.datetime import parseDatetimetz
from gs.group.list.base import EmailMessage
from Products.XWFCore.XWFUtils import removePathsFromFilenames
from .queries import (EmailMessageStorageQuery, FileMetadataStorageQuery)


class EmailMessageStore(EmailMessage):

    def __init__(self, context, message, list_title='', group_id='',
                 site_id='', sender_id_cb=None, replace_mail_date=True):
        super(EmailMessageStore, self).__init__('', list_title, group_id,
                                                site_id, sender_id_cb)
        self.context = context
        self.message = message
        self.replace_mail_date = replace_mail_date

    @classmethod
    def from_email_message(cls, context, emailMessage,
                           replaceMailDate=True):
        retval = cls(context, emailMessage.message, emailMessage.list_title,
                     emailMessage.group_id, emailMessage.site_id,
                     emailMessage.sender_id_cb, replaceMailDate)
        return retval

    @Lazy
    def emailQuery(self):
        retval = EmailMessageStorageQuery(self)
        return retval

    @Lazy
    def fileQuery(self):
        retval = FileMetadataStorageQuery()
        return retval

    @Lazy
    def inreplyto(self):
        return self.message.get('in-reply-to', '')

    @Lazy
    def attachment_count(self):
        count = 0
        for item in self.attachments:
            if item['filename']:
                count += 1
        return count

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

    def store(self):
        """ Store mail & attachments in a folder and return it."""
        logMsg = 'Storing post "{0}"'.format(self.post_id)
        log.info(logMsg)

        self.emailQuery.insert()
        # --=mpj17=-- The file meatadata can only be added once the
        # email is stored.
        fileMetadata = []
        for attachment in self.attachments:
                d = self.store_attachment(attachment)
                if d is not None:
                    fileMetadata.append(d)
        self.fileQuery.insert_metadata(fileMetadata)
        fileIds = [f['file_id'] for f in fileMetadata]
        return (self.post_id, fileIds)

    def store_attachment(self, attachment):
        retval = None
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
            m = '{0} ({1}): archiving HTML message.'
            logMsg = m.format(self.list_title, self.group_id)
            log.info(logMsg)
        elif attachment['contentid'] and (attachment['filename'] == ''):
            # TODO: What do we want to do with these? They are typically
            # part of an HTML message, for example the images, but what
            # should we do with them once we've stripped them?
            m = '%s (%s): stripped, but not archiving %s attachment '\
                '%s; it appears to be part of an HTML message.' % \
                (self.list_title, self.group_id,
                 attachment['maintype'], attachment['filename'])
            log.info(m)
        elif attachment['length'] <= 0:
            # Empty attachment. Kinda pointless archiving this!
            m = '%s (%s): stripped, but not archiving %s attachment '\
                '%s; attachment was of zero size.' % \
                (self.list_title, self.group_id,
                 attachment['maintype'], attachment['filename'])
            log.warn(m)
        else:
            m = '{0} ({1}): stripped and archiving {2} attachment {3}'
            logMsg = m.format(self.list_title, self.group_id,
                              attachment['maintype'],
                              attachment['filename'])
            log.info(logMsg)

            fileId = self.add_file(attachment, self.subject, self.sender_id)
            filename = removePathsFromFilenames(attachment['filename'])
            retval = {'file_id': fileId,
                      'mime_type': attachment['mimetype'],
                      'file_name': filename,
                      'file_size': attachment['length'],
                      'date': self.date,
                      'post_id': self.post_id,
                      'topic_id': self.topic_id}
        return retval

    @Lazy
    def storage(self):
        # Warning: Aquisition
        retval = self.context.FileLibrary2.get_fileStorage()
        return retval

    def add_file(self, attachment, topic, creator):
        """ Adds an attachment as a file."""
        fileId = self.storage.add_file(attachment['payload'])
        fileObj = self.storage.get_file(fileId)
        fixedTitle = removePathsFromFilenames(attachment['filename'])
        fileObj.manage_changeProperties(
            content_type=attachment['mimetype'], title=fixedTitle,
            tags=['attachment'], group_ids=[self.group_id],
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
