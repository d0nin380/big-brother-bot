#       README-Dirc.txt
# 		Plugin for B3 (www.bigbrotherbot.com)
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

Description:
		IRC Plugin for b3
		This plugin will be able to handle admin commands such as kick/ban from IRC... In the future...
		
		This should probably be converted
		to a parser instead of a plugin.
	
		I'm working on speed and b3 core changes
		to make it working with most of the games.
		Currently confirmed working games:
			cod4
		Currently confirmed working IRC servers:
			quakenet


		

Installation:
	1. Unzip the content of this package into your B3 folder. It will
	place the Dirc.py file in b3/extplugins and the config file Dirc.xml in
	your b3/extplugins/conf folder.

	2. Open Dirc.xml with your texteditor and edit the bot name and server info.

	3. Open your B3.xml file (in b3/conf) and add the next line in the
	<plugins> section of the file:

		<plugin config="@b3/extplugins/conf/dirc.xml" name="dirc" />

	4. Restart your b3
	
Support:
	Support will ONLY be provided in http://forum.bigbrotherbot.net/releases/dirc-plugin/ so do not email me or anybody else your support questions.
	
# CHANGELOG
#   2013/03/01 - 1.0.0 - d0nin380
#	   * Initial Release
#   2013/03/03 - 1.0.1 - d0nin380
#   	* Add bot auth in quakenet
#		* Cleaned up irc_parser
#		* Fixed a bug where pong was sent 
#		* 	with the next msg in buffer
#		*	instead of the actual ping
#		* Added some error handling
#	2013/03/20 - 1.1.0 - d0nin380
#		* Add events handling
#		* fixed bugs
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
