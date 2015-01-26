=======================
``gs.group.list.store``
=======================
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Store email messages posted to a mailing-list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Author: `Michael JasonSmith`_
:Contact: Michael JasonSmith <mpj17@onlinegroups.net>
:Date: 2015-01-26
:Organization: `GroupServer.org`_
:Copyright: This document is licensed under a
  `Creative Commons Attribution-Share Alike 4.0 International License`_
  by `OnlineGroups.net`_.

..  _Creative Commons Attribution-Share Alike 4.0 International License:
    http://creativecommons.org/licenses/by-sa/4.0/

Introduction
============

Messages in GroupServer_ are stored in the PostgreSQL relational
database. This product defines interface_ and the default
adaptor_ that stores the messages.

Interface
=========

The core email processing system
(``Products.XWFMailingListManager`` [#list]_) adapts a group
[#group]_ and a message [#message]_ to the interface
``gs.group.list.store.interfaces.IStorageForEmailMessage``. Classes
that conform to this interface must provide a ``store`` method
that stores the message.

Adaptor
=======

The ``gs.group.list.store..messagestore.EmailMessageStore``
adaptor stores an email in the PostgreSQL database. The database
table itself is defined by the Post code [#post]_.


Resources
=========

- Code repository: https://github.com/groupserver/gs.group.list.store
- Questions and comments to http://groupserver.org/groups/development
- Report bugs at https://redmine.iopen.net/projects/groupserver

.. _GroupServer: http://groupserver.org/
.. _GroupServer.org: http://groupserver.org/
.. _OnlineGroups.Net: https://onlinegroups.net
.. _Michael JasonSmith: http://groupserver.org/p/mpj17

.. [#list] See
           <https://github.com/groupserver/Products.XWFMailingListManager>
.. [#group] A group provides the
            ``gs.group.base.interfaces.IGSGroupMarker`` interface
            <https://github.com/groupserver/gs.group.base>
.. [#message] A message provides the
            ``gs.group.list.base.interfaces.IEmailMessage``
            interface
            <https://github.com/groupserver/gs.group.list.base>
.. [#post] See ``gs.group.messages.post``
           <https://github.com/groupserver/gs.group.messages.post>
