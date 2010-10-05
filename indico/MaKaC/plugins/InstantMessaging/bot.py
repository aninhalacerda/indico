import sleekxmpp

from MaKaC.services.interface.rpc.common import ServiceError

class IndicoJabberBotBase(object):

    def __init__(self, jid, password):
        self.xmpp = sleekxmpp.ClientXMPP(jid, password)
        self.xmpp.registerPlugin('xep_0045')
        self.xmpp.registerPlugin('xep_0004')
        self.xmpp.registerPlugin('xep_0030')
        self.xmpp.add_event_handler("session_start", self.handleXMPPConnected)

    def formDefaults(self, form):
        form.addField(var = 'muc#roomconfig_publicroom', value = '1')
        form.addField(var = 'public_list', value = '1')
        form.addField(var = 'muc#roomconfig_whois', value = 'moderators')
        form.addField(var = 'muc#roomconfig_membersonly', value = '0')
        form.addField(var = 'muc#roomconfig_moderatedroom', value = '1')
        form.addField(var = 'members_by_default', value = '1')
        form.addField(var = 'muc#roomconfig_changesubject', value = '1')
        form.addField(var = 'allow_private_messages', value = '1')
        form.addField(var = 'allow_query_users', value = '1')
        form.addField(var = 'muc#roomconfig_allowinvites', value = '1')
        form.addField(var = 'muc#roomconfig_allowvisitorstatus', value = '1')
        form.addField(var = 'muc#roomconfig_allowvisitornickchange', value = '1')
        form.addField(var = 'muc#roomconfig_enablelogging', value = '1')
        #form.addField(var = 'muc#roomconfig_maxusers', value = '1000')

    def handleXMPPConnected(self, event):
        pass


class IndicoJabberBotCreateRoom(IndicoJabberBotBase):

    def __init__(self, jid, password, room):
        IndicoJabberBotBase.__init__(self, jid, password)
        self._room = room
        self._protected = 1 if self._room.getPassword() != '' else 0
        self._nick, server = jid.split('@')
        self._jid = self._room.getTitle() + '@conference.' + server

        try:
            connected = self.xmpp.connect()
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()
        self.xmpp.process(threaded=False)

    def handleXMPPConnected(self, event):
        muc = self.xmpp.plugin['xep_0045']

        try:
            muc.joinMUC(room = self._jid, nick = self._nick)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()

        form = self.xmpp.plugin['xep_0004'].makeForm()

        form.addField('FORM_TYPE', value='http://jabber.org/protocol/muc#roomconfig')
        self.formDefaults(form)
        form.addField(var = 'muc#roomconfig_roomname', value = self._room.getTitle())

        #FYI: If a field is empty ejabberd will answer with a bad request error, so if the field's value is empty do not send it!
        if self._room.getDescription():
            form.addField(var = 'muc#roomconfig_roomdesc', value = self._room.getDescription())
        if self._protected:
            form.addField(var = 'muc#roomconfig_passwordprotectedroom', value = str(self._protected))
            form.addField(var = 'muc#roomconfig_roomsecret', value = self._room.getPassword())

        form.addField(var = 'muc#roomconfig_persistentroom', value = '1')

        self._error = False
        try:
            self._error = not muc.configureRoom(self._jid, form)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()

        self.xmpp.disconnect()


class IndicoJabberBotEditRoom(IndicoJabberBotBase):

    def __init__(self, jid, password, room):
        IndicoJabberBotBase.__init__(self, jid, password)
        self._room = room
        self._protected = 1 if self._room.getPassword() != '' else 0
        self._nick, server = jid.split('@')
        self._jid = self._room.getTitle() + '@conference.' + server
        self._error = False

        try:
            self.xmpp.connect()
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()
        self.xmpp.process(threaded=False)

    def handleXMPPConnected(self, event):
        muc = self.xmpp.plugin['xep_0045']

        try:
            muc.joinMUC(room = self._jid, nick = self._nick)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()
        #import pydevd; pydevd.settrace(stdoutToServer = True, stderrToServer = True)
        form = self.xmpp.plugin['xep_0004'].makeForm()

        form.addField('FORM_TYPE', value='http://jabber.org/protocol/muc#roomconfig')
        self.formDefaults(form)
        form.addField(var = 'muc#roomconfig_roomname', value = self._room.getTitle())

        #FYI: If a field is empty ejabberd will answer with a bad request error, so if the field's value is empty do not send it!
        if self._room.getDescription():
            form.addField(var = 'muc#roomconfig_roomdesc', value = self._room.getDescription())
        form.addField(var = 'muc#roomconfig_passwordprotectedroom', value = str(self._protected))
        if self._protected:
            form.addField(var = 'muc#roomconfig_roomsecret', value = self._room.getPassword())

        form.addField(var = 'muc#roomconfig_persistentroom', value = '1')

        try:
            self._error = not muc.configureRoom(self._jid, form)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()

        self.xmpp.disconnect()


class IndicoJabberBotDeleteRoom(IndicoJabberBotBase):

    def __init__(self, jid, password, room, reason):
        IndicoJabberBotBase.__init__(self, jid, password)
        self._room = room
        self._protected = 1 if self._room.getPassword() != '' else 0
        self._nick, server = jid.split('@')
        self._jid = self._room.getTitle() + '@conference.' + server
        self._reason = reason
        self._error = False

        try:
            self.xmpp.connect()
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()
        self.xmpp.process(threaded=False)

    def handleXMPPConnected(self, event):
        muc = self.xmpp.plugin['xep_0045']
        try:
            muc.joinMUC(room = self._jid, nick = self._nick)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()

        try:
            self.xmpp.sendMessage(self._jid, self._reason, mtype='groupchat')
            self._error = not muc.destroy(self._jid, self._reason)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()

        self.xmpp.disconnect()


class IndicoJabberBotGetPreferences(IndicoJabberBotBase):

    def __init__(self, jid, password, room):
        IndicoJabberBotBase.__init__(self, jid, password)
        self._room = room
        self._nick, server = jid.split('@')
        self._jid = self._room.getTitle() + '@conference.' + server

        try:
            self.xmpp.connect()
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()
        self.xmpp.process(threaded=False)

    def handleXMPPConnected(self, event):
        muc = self.xmpp.plugin['xep_0045']
        try:
            self._form = muc.getRoomConfig(self._jid)
        except Exception, e:
            self._error = True
            self.xmpp.disconnect()

        self.xmpp.disconnect()