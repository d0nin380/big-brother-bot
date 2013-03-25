#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       dirc.py
#
#       Copyright 2013 d0nin380 <d0nin380<at>gmail<dot>com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
#       B3 IRC Plugin to chat/admin from IRC
#       This should probably be converted
#       to a parser instead of a plugin.
#   
#       I'm working on speed and b3 core changes
#       to make it working with most of the games.
#       Currently confirmed working games:
#           cod4
#       Currently confirmed working IRC servers:
#           quakenet

# CHANGELOG
#   2013/03/01 - 1.0.0 - d0nin380
#      * Initial Release
#   2013/03/03 - 1.0.1 - d0nin380
#       * Add bot auth in quakenet
#       * Cleaned up irc_parser
#       * Fixed a bug where pong was sent 
#       *   with the next msg in buffer
#       *   instead of the actual ping
#       * Added some error handling
#   2013/03/20 - 1.1.0 - d0nin380
#       * Add events handling
#       * fixed bugs
#   2013/03/21 -1.1.1 - d0nin380
#       *fixed a bug in OnPrivmsg
#       *chat prefix can be left empty to send all messages in channel to game server
#       *identation matches b3 identation
#       *fixed file names
#   2013/03/24 - 1.1.2 - d0nin380
#       *removed cron when plugin gets disabled after too many reconnect tries
#       *fixed a typo in disabling plugin
#       *fixed the config line in README-Dirc.txt
#       *added support for irc.rizon.net


__version__ = '1.1.2'
__author__ = 'd0nin380'

import b3,b3.events,socket,time,b3.cron,re

class DircPlugin(b3.plugin.Plugin):
    """
    B3 IRC Plugin to chat/admin from IRC
    This should probably be converted
    to a parser instead of a plugin.
    
    I'm working on speed and b3 core changes
    to make it working with most of the games.
    Currently confirmed games working games:
        cod4
    Currently confirmed working IRC servers:
        quakenet
    """
    _cronTab = None
    
    def onLoadConfig(self):
        """
        Loading necessary values from config
        """
        try:
            self.irc_server = self.config.get('settings', 'server')
            self.irc_port = self.config.getint('settings', 'port')
            self.irc_nick = self.config.get('settings', 'nick')
            self.irc_channel = self.config.get('settings','channel')
            self.irc_chat_prefix = self.config.get('settings','bot_chat_prefix')
            self.irc_cmd_prefix = self.config.get('settings','bot_cmd_prefix')
            self.irc_botauth = self.config.get('settings','botauth')
            self.irc_sock_timeout = (self.config.getint('settings','timeout'))
            
        except Exception, err:
            self.error('Config file error... %s'%err)
    
        
    def onStartup(self):
        """
        Plugin startup
        """

        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False
        
        ##################
        # Events
        ##################
        
        self._lineFormats = (
            # Auth
            re.compile(r'^(?P<action>[NOTICE]+)\s(?P<nick>[AUTH]+).+\*{3}\s(?P<data>.+)$',re.I),
            # Ping
            re.compile(r'^(?P<action>ping)\s(?P<data>.+)$',re.I),
            # Numeric events in self.irc_numerics, event = onIrcNumeric
            re.compile(r'^:(?P<server>.+)\s(?P<action>\d+)\s(?P<nick>.+)\s:(?P<data>.+)$',re.I),
            # Message
            re.compile(r'^:(?P<data>(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+))\s(?P<action>PRIVMSG)(?P<data2>\s(?P<channel>\#[\w]+)\s:(?P<text>.*))$',re.I),
            # Mode
            re.compile(r'^:(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+)\s(?P<action>MODE)\s(?P<data>.+)$',re.I),
            # Join
            re.compile(r'^:(?P<data>(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+))\s(?P<action>JOIN)\s(?P<data2>(?P<channel>\#.+))$',re.I),
            # Quit/Part
            re.compile(r'^:(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+)\s(?P<action>QUIT)\s(?P<data>(?P<channel>\#[\w]+)\s(?P<text>.*))$',re.I),
            re.compile(r'^:(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+)\s(?P<action>PART)\s(?P<data>(?P<channel>\#[\w]+)\s(?P<text>.*))$',re.I),
            # Server Notice
            re.compile(r'^:(?P<server>.+)\s(?P<action>NOTICE)\s(?P<snick>[\w]+)\s(?P<data>.*)$',re.I),
            # Notice
            re.compile(r'^:(?P<data>(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+))\s(?P<action>NOTICE)\s(?P<data2>(?P<snick>[\w]+)\s(?P<text>.*))$',re.I),
            # Query
            re.compile(r'^:(?P<data>(?P<nick>.+)!(?P<ident>.+)@(?P<host>.+))\s(?P<action>PRIVMSG)\s(?P<data2>(?P<snick>[\w]+)\s(?P<text>.+))$',re.I),
            # Error
            re.compile(r'^(?P<action>ERROR)\s:(?P<data>.*)$',re.I),
            )
        
        # IRC Numeric replies currently in use
        self.irc_numerics = {
            '001': 'IRC Welcome',
            '002': 'IRC Server Info',
            '003': 'IRC Server Info',
            '004': 'IRC Server Info',
            '005': 'IRC Server Info', 
            '221': 'IRC User Modes',
            '251': 'IRC Lusers Clients',
            '252': 'IRC Lusers Operators',
            '253': 'IRC Lusers Unknown',
            '254': 'IRC Lusers Channels',
            '255': 'IRC Lusers Local',
            '353': 'IRC Names',
            '366': 'IRC End of Names',
            '372': 'IRC MOTD',
            '375': 'IRC MOTD Start',
            '376': 'IRC End of MOTD',
            '396': 'IRC Confirm hidden host' 
            }
        
        #Register events
        self.registerEvent(b3.events.EVT_CLIENT_SAY)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_SAY)
        
        self.eventHandlers = {
            b3.events.EVT_CLIENT_SAY: self.onChat,
            b3.events.EVT_CLIENT_TEAM_SAY: self.onChat,
            }
        
        self.debug('Started')
        
    def start(self):
        
        #Connect the IRC socket
        self.verbose('Trying to connect: %s'%self.irc_server)
        self.irc = socket.socket()
        self.irc.connect((self.irc_server,self.irc_port))
        self.irc_reconnect_tries = 0
        self.irc_readbuffer = ''
                
        #set the IRC socket to be read every 5 sec
        if self._cronTab:
            self.console.cron - self._cronTab
        self._cronTab = b3.cron.PluginCronTab(self, self.irc_read, '0-59/5')
        self.console.cron + self._cronTab
        
            
    def onEvent(self,event):
        if event.type in self.eventHandlers:
            self.eventHandlers[event.type](event)
        
    def onChat(self, event):
        """
        Send messages from gameserver to IRC
        """
        client = event.client
        text = event.data
        msg = 'PRIVMSG %s :%s: %s\r\n'%(self.irc_channel,client.name,text)
        self.irc_send(msg)
    
    def OnPing(self,action,data,match=None):
        """
        PING :servercentral.il.us.quakenet.org
        or
        Initial ping is numeric, PING :123456789
        """
        if data:
            self.irc_send('PONG %s\r\n'%data)
    
    def OnJoin(self,action,data,match=None):
        """
        :dIRCBot!~dIRCBot@d0nin380.users.quakenet.org JOIN #dIRCBot
        """
        nick = match.group('nick')
        if nick != self.irc_nick:
            self.console.say('%s joined IRC' %nick)
    
    def OnQuit(self,action,data,match=None):
        """
        Quit in irc, client disconnect
        :dIRCBot!~dIRCBot@d0nin380.users.quakenet.org QUIT #dircbot :rejoining.
        """
        nick = match.group('nick')
        text = match.group('text')
        self.onLeave(nick,text)

    def OnPart(self,action,data,match=None):
        """
        Part in irc, somebody left the channel but didn't quit
        :dIRCBot!~dIRCBot@d0nin380.users.quakenet.org PART #dircbot :rejoining.
        """
        nick = match.group('nick')
        text = match.group('text')
        self.onLeave(nick,text)

    def onLeave(self,nick,text):
        """
        Combined QUIT/PART
        Called by OnPart, OnQuit
        """
        
        self.console.say('%s Left IRC: %s'%(nick, text))

    def OnNotice(self,action,data,match=None):
        """
        :portlane.se.quakenet.org NOTICE MWTCBot :Highest connection count: 10933 (10932 clients)'
        """
        text = match.group('data')
        self.verbose('this notice: %s'%text)
        if 'no ident response' in text.lower():
            self.auth()
                
    def OnMode(self,action,data,match=None):
        """
        Events for usermodes
        :dIRCBot!~dIRCBot@d0nin380.users.quakenet.org MODE dIRCBot +x
        """
        pass
        
    def OnPrivmsg(self,action,data,match=None):
        """
        :dIRCBot!~dIRCBot@d0nin380.users.quakenet.org PRIVMSG #dIRCBot :hey
        """                     
        nick = match.group('nick')
        text = match.group('text')
        if self.irc_chat_prefix:
            if text.startswith(self.irc_chat_prefix):
                self.console.say('[IRC]%s: %s'%(nick,text[1:]))
        else:
            self.console.say('[IRC]%s: %s'%(nick,text))
    
    def OnError(self,action,data,match=None):
        """
        ERROR :Closing Link: dIRCBot by underworld1.no.quakenet.org (Registration Timeout)
        """
        err = match.group('data')
        if 'throttled' in err.lower():
            self.verbose('Throttled by server... trying to reconnect in 10 sec...')
            time.sleep(10)
        
            
        self.irc_disconnect(reconnect=True)
        
    def onIrcNumeric(self,event):
        """
        Handle IRC Numeric Replies
        The bot will catch numeric replies with action \d+
        To add more numeric events to handle, the numeric event
        has to be defined in self.irc_numerics
        Value is not important as it is only for reference and
        never read by the parser
        
        :port80b.se.quakenet.org 001 dIRCBot :Welcome to the QuakeNet IRC Network, dIRCBot
        """
        
        action,data = event.data
        
        #end of motd. join channel
        if action == '376':
            self.irc_login()
            self.irc_join()
        
        
    
    ###################################################
    # Functions for linking IRC account to game server
    # Not In Use, Enable in the future
    ###################################################
    #
    # We dont need this yet
    #
    #def getCmd(self, cmd):
    #   cmd = 'cmd_%s' % cmd
    #   dir(self)
    #   if hasattr(self, cmd):
    #       func = getattr(self, cmd)
    #       return func
        
    #def _cmd_ia(self, data, client, cmd=None):
    #   """
    #   Use this command to link your IRC account
    #   NIU Enabled in the future
    #   """
    #   _dump = {}
    #   
    #   for _d in self.console.write('dumpuser %s'%client.name).strip().split('\n'):
    #       _d = ' '.join(_d.split()).split()
    #       try:
    #           _dump[_d[0]] = _d[1]
    #       except Exception, err:
    #           pass    
    #   self.irc_password = _dump['password']
    #
    ###################################################
    # /Functions for linking IRC account to game server
    ###################################################
        
    def irc_connect(self):
        """
        Connect to the IRC server
        """
        self.debug('Setting up the IRC socket...')
        self.irc = socket.socket()
        self.irc.settimeout(self.irc_sock_timeout)
        self.debug('Socket timeout set to: %s'%self.irc_sock_timeout)
        self.debug('Connecting...')
        self.irc.connect((self.irc_server,self.irc_port))
    
    def irc_reconnect(self):
        """
        Try to reconnect only 3 times
        Give up if no success
        """
        self.irc_reconnect_tries += 1
        if self.irc_reconnect_tries == 1:
            self.verbose('Trying to reconnect: %s <retries: %s>'%(self.irc_server,self.irc_reconnect_tries))
            self.irc_connect()
            
        else:
            self.verbose('Too many reconnect tries, giving up...')
            self.irc_disconnect()
            
    def irc_disconnect(self, reconnect=None):
        """
        Disconnect from IRC, reconnect if set,
        otherwise disable the plugin/close sockets
        """
        if reconnect:
            self.verbose('Resetting IRC socket and reconnecting...')
            self.irc.close()
            self.irc_reconnect()
        else:
            self.verbose('Closing IRC socket and disabling plugin...')
            _plugin = self.console.getPlugin('dirc')
            self.irc.close()
            self.console.cron - self._cronTab
            _plugin.disable()
            
            
            

    def auth(self):
        """
        Register with the server
        Called after we find "Found your hostname" in "NOTICE AUTH"
        """
        self.verbose('Registering bot with IRC server...')
        self.irc_send('USER %s 0 * :B3 IRC Plugin %s - d0nin380\r\n'%(self.irc_nick,__version__))
        self.irc_send('NICK %s\r\n'%self.irc_nick)
        
    def irc_send(self,msg):
        """
        Send messages to irc
        """
        self.verbose('Sending: %s'%msg)
        self.irc.send(msg)

    def irc_join(self):
        """
        Join the channel set in the config
        """
        self.verbose('Joining %s'%self.irc_channel)
        self.irc_send('JOIN %s\r\n'%self.irc_channel)
        
    def irc_login(self):
        """
        Called only if botauth set in config
        Auth the bot with Q/nickserv what ever the ircd uses.
        """
        if self.irc_botauth:
            self.irc_send('PRIVMSG Q@CServe.quakenet.org :AUTH %s\r\n'%self.irc_botauth)
            self.irc_send('MODE %s +x\r\n'%self.irc_nick)
    
    def change_nick(self):
        """
        In case the nick is already in use
        or the bot owner wants to change
        the name back
        """
        
        self.tries = 1
        if self.tries <= 3:
            self.irc_send('NICK %s%s'%(self.irc_nick,self.tries))
        else:
            self.verbose('Nickname already in use. Too many tries, Giving up...')
            self.irc_disconnect()

    def irc_read(self):
        """
        Keep reading the data from IRC socket untill timeout
        """
        
        while 1:
            try:
                self.irc_readbuffer=self.irc_readbuffer+self.irc.recv(1024)
                temp=self.irc_readbuffer.split("\r\n")
                self.irc_readbuffer=temp.pop( )
        
                for line in temp:
                    self.parseLine(line)
                        
            except Exception, err:
                if not 'timed out' in err or not 'Errno 9' in err:
                    self.debug('Exception in irc_read: "%s"'%err)
                    self.irc_disconnect(1)
                break
                    
    def getLineParts(self, line):
        """
        Borrowed from abstractParser.py
        Might need to be changed for other
        games than cod
        """
        
        m = None
        for f in self._lineFormats:
            m = re.match(f, line)
            if m:
                break

        if m:
            client = None
            target = None
            return m, m.group('action').lower(), m.group('data'), client, target
        #elif '------' not in line:
          #self.verbose('line did not match format: %s' % line)      
    
    def parseLine(self, line):
        """
        Borrowed from abstractParser.py
        """
        self.verbose(line)     
        m = self.getLineParts(line)
        if not m:
            return False

        match, action, data, client, target = m
        
        func = 'On%s' % action.title().replace(' ','')
        
        if hasattr(self, func):
            #self.debug('OnFunc defined, %s'%func)
            func = getattr(self, func)
            event = func(action, data, match)
            
            if event:
                self.console.queueEvent(event)
                
        elif action in self.irc_numerics:
            #self.debug('action in self.irc_numerics, %s'%action)
            self.onIrcNumeric(b3.events.Event('EVT_IRC_NUMERIC',
                    (action,data),
                    client,target
                ))
            
        else:
            #self.debug('unknown event, %s'%action)
            self.console.queueEvent(b3.events.Event(
                    b3.events.EVT_UNKNOWN,
                    str(action) + ': ' + str(data),
                    client,
                    target
                ))
            
            
