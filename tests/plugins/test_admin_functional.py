#
# BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2011 Courgette
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
import logging

from mock import Mock, call, patch, ANY
import sys, os, thread
import time
from mockito import when
import unittest2 as unittest

from b3 import __file__ as b3_module__file__, TEAM_BLUE, TEAM_RED
from b3.clients import Group

from tests import B3TestCase
from b3.fake import FakeClient
from b3.config import XmlConfigParser
from b3.plugins.admin import AdminPlugin

ADMIN_CONFIG_FILE = os.path.join(os.path.dirname(b3_module__file__), "conf/plugin_admin.xml")

class Admin_functional_test(B3TestCase):
    """ tests from a class inherithing from Admin_functional_test must call self.init() """
    def setUp(self):
        B3TestCase.setUp(self)
        self.conf = XmlConfigParser()
        self.p = AdminPlugin(self.console, self.conf)

    def init(self, config_content=None):
        """ optionally specify a config for the plugin. If called with no parameter, then the default config is loaded """
        if config_content is None:
            if not os.path.isfile(ADMIN_CONFIG_FILE):
                B3TestCase.tearDown(self) # we are skipping the test at a late stage after setUp was called
                raise unittest.SkipTest("%s is not a file" % ADMIN_CONFIG_FILE)
            else:
                self.conf.load(ADMIN_CONFIG_FILE)
        else:
            self.conf.loadFromString(config_content)
        self.p._commands = {}
        self.p.onLoadConfig()
        self.p.onStartup()

        self.joe = FakeClient(self.console, name="Joe", exactName="Joe", guid="joeguid", groupBits=128, team=TEAM_RED)
        self.mike = FakeClient(self.console, name="Mike", exactName="Mike", guid="mikeguid", groupBits=1, team=TEAM_BLUE)


class Cmd_tempban(Admin_functional_test):

    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.message = Mock()
        self.joe.connects(0)

    def test_no_duration(self):
        self.mike.connects(1)
        self.joe.says('!tempban mike')
        self.joe.message.assert_called_with('^7Invalid parameters')

    def test_bad_duration(self):
        self.mike.connects(1)
        self.mike.tempban = Mock()
        self.joe.says('!tempban mike 5hour')
        self.joe.message.assert_called_with('^7Invalid parameters')
        assert not self.mike.tempban.called

    def test_non_existing_player(self):
        self.mike.connects(1)
        self.joe.says('!tempban foo 5h')
        self.joe.message.assert_called_with('^7No players found matching foo')

    def test_no_reason(self):
        self.mike.connects(1)
        self.mike.tempban = Mock()
        self.joe.says('!tempban mike 5h')
        self.mike.tempban.assert_called_with('', None, 5*60, self.joe)


class Cmd_lastbans(Admin_functional_test):

    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.message = Mock()
        self.joe.connects(0)

    def test_no_ban(self):
        self.joe.says('!lastbans')
        self.joe.message.assert_called_with('^7There are no active bans')

    @patch('time.time', return_value=0)
    def test_one_tempban(self, mock_time):
        # GIVEN
        self.mike.connects(1)
        # WHEN
        self.joe.says('!tempban mike 5h test reason')
        self.joe.says('!lastbans')
        # THEN
        self.joe.message.assert_called_with(u'^2@2^7 Mike^7^7 (5 hours remaining) test reason')
        # WHEN
        self.joe.says('!unban @2')
        self.joe.says('!lastbans')
        # THEN
        self.joe.message.assert_called_with('^7There are no active bans')



class Cmd_help(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.p._commands = {}  # make sure to empty the commands list as _commands is a wrongly a class property
        self.init()
        self.joe.message = Mock()
        self.joe.connects(0)

    def test_non_existing_cmd(self):
        self.joe.says('!help fo0')
        self.joe.message.assert_called_with('^7Command not found fo0')

    def test_existing_cmd(self):
        self.joe.says('!help help')
        self.joe.message.assert_called_with('^2!help ^7%s' % self.p.cmd_help.__doc__.strip())

    def test_no_arg(self):
        self.joe.says('!help')
        self.joe.message.assert_called_with('^7Available commands: admins, admintest, aliases, b3, ban, banall, baninfo,'
                                            ' clear, clientinfo, die, disable, enable, find, help, iamgod, kick, kickall, lastbans'
                                            ', leveltest, list, lookup, makereg, map, maprotate, maps, mask, nextmap, no'
                                            'tice, pause, permban, poke, putgroup, rebuild, reconfig, regtest, regulars, restart, '
                                            'rules, runas, say, scream, seen, spam, spams, spank, spankall, status, temp'
                                            'ban, time, unban, ungroup, unmask, unreg, warn, warnclear, warninfo, warnremove, w'
                                            'arns, warntest')
        self.mike.message = Mock()
        self.mike.connects(0)
        self.mike.says('!help')
        self.mike.message.assert_called_with('^7Available commands: help, iamgod, regtest, regulars, rules, time')

    def test_joker(self):
        self.joe.says('!help *ban')
        self.joe.message.assert_called_with('^7Available commands: ban, banall, baninfo, lastbans, permban, tempban, unban')


class Cmd_mask(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()

    def test_nominal(self):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        # only superadmin joe is connected
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7]')
        # introducing mike (senioradmin)
        self.mike.connects(1)
        self.joe.says('!putgroup mike senioradmin')
        # we know have 2 admins connected
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7], Mike^7^7 [^380^7]')
        # joe masks himself as a user
        self.joe.says('!mask user')
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Mike^7^7 [^380^7]')
        # joe unmasks himself
        self.joe.says('!unmask')
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7], Mike^7^7 [^380^7]')
        # joe masks mike as a user
        self.joe.says('!mask user mike')
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7]')
        # joe unmasks mike
        self.joe.says('!unmask mike')
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7], Mike^7^7 [^380^7]')


class Cmd_makereg_unreg(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.group_user = self.console.storage.getGroup(Group(keyword='user'))
        self.group_reg = self.console.storage.getGroup(Group(keyword='reg'))
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.mike.connects(1)

    def test_nominal(self):
        # GIVEN
        self.assertTrue(self.mike.inGroup(self.group_user))
        self.assertFalse(self.mike.inGroup(self.group_reg))
        # WHEN
        self.joe.says("!makereg mike")
        # THEN
        self.assertFalse(self.mike.inGroup(self.group_user))
        self.assertTrue(self.mike.inGroup(self.group_reg))
        self.joe.message.assert_called_with('^7Mike^7 ^7put in group Regular')
        # WHEN
        self.joe.says("!unreg mike")
        # THEN
        self.assertTrue(self.mike.inGroup(self.group_user))
        self.assertFalse(self.mike.inGroup(self.group_reg))
        self.joe.message.assert_called_with('^7Mike^7^7 removed from group Regular')


    def test_unreg_when_not_regular(self):
        # GIVEN
        self.assertTrue(self.mike.inGroup(self.group_user))
        self.assertFalse(self.mike.inGroup(self.group_reg))
        # WHEN
        self.joe.says("!unreg mike")
        # THEN
        self.assertTrue(self.mike.inGroup(self.group_user))
        self.assertFalse(self.mike.inGroup(self.group_reg))
        self.joe.message.assert_called_with('^7Mike^7^7 is not in group Regular')


    def test_makereg_when_already_regular(self):
        # GIVEN
        self.mike.addGroup(self.group_reg)
        self.mike.remGroup(self.group_user)
        self.assertTrue(self.mike.inGroup(self.group_reg))
        # WHEN
        self.joe.says("!makereg mike")
        # THEN
        self.assertFalse(self.mike.inGroup(self.group_user))
        self.assertTrue(self.mike.inGroup(self.group_reg))
        self.joe.message.assert_called_with('^7Mike^7^7 is already in group Regular')


    def test_makereg_no_parameter(self):
        # WHEN
        self.joe.says("!makereg")
        # THEN
        self.joe.message.assert_called_with('^7Invalid parameters')


    def test_unreg_no_parameter(self):
        # WHEN
        self.joe.says("!unreg")
        # THEN
        self.joe.message.assert_called_with('^7Invalid parameters')


    def test_makereg_unknown_player(self):
        # WHEN
        self.joe.says("!makereg foo")
        # THEN
        self.joe.message.assert_called_with('^7No players found matching foo')


    def test_unreg_unknown_player(self):
        # WHEN
        self.joe.says("!unreg foo")
        # THEN
        self.joe.message.assert_called_with('^7No players found matching foo')


def _start_new_thread(callable, args_list, kwargs_dict):
    """ used to patch thread.start_new_thread so it won't create a new thread but call the callable synchronously """
    callable(*args_list, **kwargs_dict)

@patch.object(time, "sleep")
@patch.object(thread, "start_new_thread", wraps=_start_new_thread)
class Cmd_rules(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()

    def test_nominal(self, start_new_thread_mock, sleep_mock):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.joe.says('!rules')
        self.joe.message.assert_has_calls([call('^3Rule #1: No racism of any kind'),
                                           call('^3Rule #2: No clan stacking, members must split evenly between the teams'),
                                           call('^3Rule #3: No arguing with admins (listen and learn or leave)'),
                                           call('^3Rule #4: No abusive language or behavior towards admins or other players'),
                                           call('^3Rule #5: No offensive or potentially offensive names, annoying names, or in-game (double caret (^)) color in names'),
                                           call('^3Rule #6: No recruiting for your clan, your server, or anything else'),
                                           call('^3Rule #7: No advertising or spamming of websites or servers'),
                                           call('^3Rule #8: No profanity or offensive language (in any language)'),
                                           call('^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning'),
                                           call('^3Rule #10: Offense players must play for the objective and support their team')])

    def test_nominal_loud(self, start_new_thread_mock, sleep_mock):
        self.console.say = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.joe.says('@rules')
        self.console.say.assert_has_calls([call('^3Rule #1: No racism of any kind'),
                                           call('^3Rule #2: No clan stacking, members must split evenly between the teams'),
                                           call('^3Rule #3: No arguing with admins (listen and learn or leave)'),
                                           call('^3Rule #4: No abusive language or behavior towards admins or other players'),
                                           call('^3Rule #5: No offensive or potentially offensive names, annoying names, or in-game (double caret (^)) color in names'),
                                           call('^3Rule #6: No recruiting for your clan, your server, or anything else'),
                                           call('^3Rule #7: No advertising or spamming of websites or servers'),
                                           call('^3Rule #8: No profanity or offensive language (in any language)'),
                                           call('^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning'),
                                           call('^3Rule #10: Offense players must play for the objective and support their team')])

    def test_nominal_bigtext(self, start_new_thread_mock, sleep_mock):
        self.console.saybig = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.joe.says('&rules')
        self.console.saybig.assert_has_calls([call('^3Rule #1: No racism of any kind'),
                                           call('^3Rule #2: No clan stacking, members must split evenly between the teams'),
                                           call('^3Rule #3: No arguing with admins (listen and learn or leave)'),
                                           call('^3Rule #4: No abusive language or behavior towards admins or other players'),
                                           call('^3Rule #5: No offensive or potentially offensive names, annoying names, or in-game (double caret (^)) color in names'),
                                           call('^3Rule #6: No recruiting for your clan, your server, or anything else'),
                                           call('^3Rule #7: No advertising or spamming of websites or servers'),
                                           call('^3Rule #8: No profanity or offensive language (in any language)'),
                                           call('^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning'),
                                           call('^3Rule #10: Offense players must play for the objective and support their team')])

    def test_nominal_to_player(self, start_new_thread_mock, sleep_mock):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.mike.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.mike.connects(1)
        self.joe.says('!rules mike')
        self.mike.message.assert_has_calls([call('^3Rule #1: No racism of any kind'),
                                           call('^3Rule #2: No clan stacking, members must split evenly between the teams'),
                                           call('^3Rule #3: No arguing with admins (listen and learn or leave)'),
                                           call('^3Rule #4: No abusive language or behavior towards admins or other players'),
                                           call('^3Rule #5: No offensive or potentially offensive names, annoying names, or in-game (double caret (^)) color in names'),
                                           call('^3Rule #6: No recruiting for your clan, your server, or anything else'),
                                           call('^3Rule #7: No advertising or spamming of websites or servers'),
                                           call('^3Rule #8: No profanity or offensive language (in any language)'),
                                           call('^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning'),
                                           call('^3Rule #10: Offense players must play for the objective and support their team')])

    def test_unknown_player(self, start_new_thread_mock, sleep_mock):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.joe.says('!rules fOO')
        self.joe.message.assert_has_calls([call('^7No players found matching fOO')])


class Cmd_warns(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()

    def test_nominal(self):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.joe.says('!warns')
        self.joe.message.assert_called_once_with('^7Warnings: adv, afk, argue, badname, camp, ci, color, cuss, fakecmd,'
        ' jerk, lang, language, name, nocmd, obj, profanity, racism, recruit, rule1, rule10, rule2, rule3, rule4, rule5'
        ', rule6, rule7, rule8, rule9, sfire, spam, spawnfire, spec, spectator, stack, tk')


class Test_warn_reasons_default_config(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.connects(0)
        self.mike.connects(1)

    def test_no_reason(self):
        with patch.object(self.mike, "warn") as mock:
            self.joe.says('!warn mike')
            mock.assert_has_calls([call(60.0, '^7behave yourself', None, self.joe, '')])

    def test_reason_is_not_a_keyword(self):
        with patch.object(self.mike, "warn") as mock:
            self.joe.says('!warn mike f00')
            mock.assert_has_calls([call(60.0, '^7 f00', 'f00', self.joe, '')])

    def test_reason_is_a_keyword(self):
        with patch.object(self.mike, "warn") as warn_mock:
            def assertWarn(keyword, duration, text):
                # GIVEN
                warn_mock.reset_mock()
                self.mike.delvar(self.p, 'warnTime')
                # WHEN
                self.joe.says('!warn mike %s' % keyword)
                # THEN
                warn_mock.assert_has_calls([call(float(duration), text, keyword, self.joe, '')])

            assertWarn("rule1", 14400, '^3Rule #1: No racism of any kind')
            assertWarn("rule2", 1440, '^3Rule #2: No clan stacking, members must split evenly between the teams')
            assertWarn("rule3", 1440, '^3Rule #3: No arguing with admins (listen and learn or leave)')
            assertWarn("rule4", 1440, '^3Rule #4: No abusive language or behavior towards admins or other players')
            assertWarn("rule5", 60, '^3Rule #5: No offensive or potentially offensive names, annoying names, or in-game (double caret (^)) color in names')
            assertWarn("rule6", 1440, '^3Rule #6: No recruiting for your clan, your server, or anything else')
            assertWarn("rule7", 1440, '^3Rule #7: No advertising or spamming of websites or servers')
            assertWarn("rule8", 4320, '^3Rule #8: No profanity or offensive language (in any language)')
            assertWarn("rule9", 180, '^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning')
            assertWarn("rule10", 4320, '^3Rule #10: Offense players must play for the objective and support their team')
            assertWarn("stack", 1440, '^3Rule #2: No clan stacking, members must split evenly between the teams')
            assertWarn("lang", 4320, '^3Rule #8: No profanity or offensive language (in any language)')
            assertWarn("language", 4320, '^3Rule #8: No profanity or offensive language (in any language)')
            assertWarn("cuss", 4320, '^3Rule #8: No profanity or offensive language (in any language)')
            assertWarn("profanity", 4320, '^3Rule #8: No profanity or offensive language (in any language)')
            assertWarn("name", 60, '^3Rule #5: No offensive or potentially offensive names, annoying names, or in-game (double caret (^)) color in names')
            assertWarn("color", 60, '^7No in-game (double caret (^)) color in names')
            assertWarn("badname", 60, '^7No offensive, potentially offensive, or annoying names')
            assertWarn("spec", 5, '^7spectator too long on full server')
            assertWarn("adv", 1440, '^3Rule #7: No advertising or spamming of websites or servers')
            assertWarn("racism", 14400, '^3Rule #1: No racism of any kind')
            assertWarn("stack", 1440, '^3Rule #2: No clan stacking, members must split evenly between the teams')
            assertWarn("recruit", 1440, '^3Rule #6: No recruiting for your clan, your server, or anything else')
            assertWarn("argue", 1440, '^3Rule #3: No arguing with admins (listen and learn or leave)')
            assertWarn("sfire", 180, '^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning')
            assertWarn("spawnfire", 180, '^3Rule #9: Do ^1NOT ^3fire at teammates or within 10 seconds of spawning')
            assertWarn("jerk", 1440, '^3Rule #4: No abusive language or behavior towards admins or other players')
            assertWarn("afk", 5, '^7you appear to be away from your keyboard')
            assertWarn("tk", 1440, '^7stop team killing!')
            assertWarn("obj", 60, '^7go for the objective!')
            assertWarn("camp", 60, '^7stop camping or you will be kicked!')
            assertWarn("fakecmd", 60, '^7do not use fake commands')
            assertWarn("nocmd", 60, '^7do not use commands that you do not have access to, try using !help')
            assertWarn("ci", 5, '^7connection interupted, reconnect')
            assertWarn("spectator", 5, '^7spectator too long on full server')
            assertWarn("spam", 60, '^7do not spam, shut-up!')


class Test_reason_keywords(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.connects(0)
        self.mike.connects(1)
        self.adv_text = "^3Rule #7: No advertising or spamming of websites or servers"


    def test_warn_with_keyword(self):
        with patch.object(self.console, "say") as say_mock:
            self.joe.says('!warn mike adv')
            say_mock.assert_has_calls([call('^1WARNING^7 [^31^7]: Mike^7^7, %s' % self.adv_text)])

    def test_warn_with_unknown_keyword(self):
        with patch.object(self.console, "say") as say_mock:
            self.joe.says('!warn mike f00')
            say_mock.assert_has_calls([call('^1WARNING^7 [^31^7]: Mike^7^7, ^7 f00')])


    def test_notice_with_keyword(self):
        with patch.object(self.mike, "notice") as notice_mock:
            self.joe.says('!notice mike adv')
            notice_mock.assert_has_calls([call('adv', None, self.joe)])

    def test_notice_with_unknown_keyword(self):
        with patch.object(self.mike, "notice") as notice_mock:
            self.joe.says('!notice mike f00')
            notice_mock.assert_has_calls([call('f00', None, self.joe)])


    def test_kick_with_keyword(self):
        with patch.object(self.console, "kick") as kick_mock:
            self.joe.says('!kick mike adv')
            kick_mock.assert_has_calls([call(self.mike, self.adv_text, self.joe, False)])

    def test_kick_with_unknown_keyword(self):
        with patch.object(self.console, "kick") as kick_mock:
            self.joe.says('!kick mike f00')
            kick_mock.assert_has_calls([call(self.mike, 'f00', self.joe, False)])


    def test_ban_with_keyword(self):
        with patch.object(self.mike, "tempban") as tempban_mock:
            self.joe.says('!ban mike adv')
            tempban_mock.assert_has_calls([call(self.adv_text, 'adv', 20160.0, self.joe)])

    def test_ban_with_unknown_keyword(self):
        with patch.object(self.mike, "tempban") as tempban_mock:
            self.joe.says('!ban mike f00')
            tempban_mock.assert_has_calls([call('f00', 'f00', 20160.0, self.joe)])


    def test_permban_with_keyword(self):
        with patch.object(self.mike, "ban") as permban_mock:
            self.joe.says('!permban mike adv')
            permban_mock.assert_has_calls([call(self.adv_text, 'adv', self.joe)])

    def test_permban_with_unknown_keyword(self):
        with patch.object(self.mike, "ban") as permban_mock:
            self.joe.says('!permban mike f00')
            permban_mock.assert_has_calls([call('f00', 'f00', self.joe)])


@unittest.skipUnless(os.path.isfile(ADMIN_CONFIG_FILE), "%s is not a file" % ADMIN_CONFIG_FILE)
class Test_config(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        logging.getLogger('output').setLevel(logging.INFO)

    def test_no_generic_or_default_warn_readon(self):

        # load the default plugin_admin.xml file after having remove the 'generic' setting from section 'warn_reasons'
        from b3.lib.elementtree import ElementTree as ET
        root = ET.parse(ADMIN_CONFIG_FILE).getroot()
        warn_reasons_nodes = [x for x in root.findall('settings') if x.get('name') == 'warn_reasons' ][0]
        if len(warn_reasons_nodes):
            generic_nodes = [x for x in warn_reasons_nodes[0].findall('set') if x.get('name') == "generic"]
            if len(generic_nodes):
                warn_reasons_nodes[0].remove(generic_nodes[0])
            default_nodes = [x for x in warn_reasons_nodes[0].findall('set') if x.get('name') == "default"]
            if len(default_nodes):
                warn_reasons_nodes[0].remove(default_nodes[0])
        self.init(ET.tostring(root))

        self.joe.message = Mock(lambda x: sys.stdout.write("message to Joe: " + x + "\n"))
        self.joe.connects(0)
        self.joe.says('!warntest')
        self.joe.message.assert_called_once_with('^2TEST: ^1WARNING^7 [^31^7]: ^7behave yourself')
        self.joe.message.reset_mock()
        self.joe.says('!warntest argue')
        self.joe.message.assert_called_once_with('^2TEST: ^1WARNING^7 [^31^7]: ^3Rule #3: No arguing with admins (listen and learn or leave)')


    def test_bad_format_for_generic_and_default(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="generic">1h</set>
                            <set name="default">/</set>
                        </settings>
                    </configuration>""")
        self.assertEqual((60, "^7"), self.p.warn_reasons['generic'])
        self.assertEqual((60, "^7behave yourself"), self.p.warn_reasons['default'])

    def test_bad_format_1(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="foo">foo</set>
                            <set name="bar">5d</set>
                        </settings>
                    </configuration>""")
        self.assertNotIn('foo', self.p.warn_reasons)

    def test_bad_format_2(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="foo">/foo bar</set>
                        </settings>
                    </configuration>""")
        self.assertNotIn('foo', self.p.warn_reasons)

    def test_bad_format_3(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="foo">/spam#</set>
                            <set name="bar">/spam# qsdf sq</set>
                        </settings>
                    </configuration>""")
        self.assertNotIn('foo', self.p.warn_reasons)

    def test_reference_to_warn_reason(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="foo">2h, foo</set>
                            <set name="bar">/foo</set>
                        </settings>
                    </configuration>""")
        self.assertIn('foo', self.p.warn_reasons)
        self.assertEqual((120, 'foo'), self.p.warn_reasons['foo'])
        self.assertIn('bar', self.p.warn_reasons)
        self.assertEqual((120, 'foo'), self.p.warn_reasons['bar'])


    def test_invalid_reference_to_warn_reason(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="foo">2h, foo</set>
                            <set name="bar">/nonexisting</set>
                        </settings>
                    </configuration>""")
        self.assertIn('foo', self.p.warn_reasons)
        self.assertEqual((120, 'foo'), self.p.warn_reasons['foo'])
        self.assertNotIn('bar', self.p.warn_reasons)


    def test_reference_to_spamage(self):
        self.init("""<configuration>
                        <settings name="spamages">
                            <set name="foo">fOO fOO</set>
                        </settings>
                        <settings name="warn_reasons">
                            <set name="bar">4h, /spam#foo</set>
                        </settings>
                    </configuration>""")
        self.assertIn('bar', self.p.warn_reasons)
        self.assertEqual((240, 'fOO fOO'), self.p.warn_reasons['bar'])


    def test_invalid_reference_to_spamage(self):
        self.init("""<configuration>
                        <settings name="warn_reasons">
                            <set name="bar">4h, /spam#foo</set>
                        </settings>
                    </configuration>""")
        self.assertNotIn('bar', self.p.warn_reasons)


class Cmd_admins(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()

    def test_nominal(self):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        # only superadmin joe is connected
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7]')
        # introducing mike (senioradmin)
        self.mike.connects(1)
        self.joe.says('!putgroup mike senioradmin')
        # we know have 2 admins connected
        self.joe.says('!admins')
        self.joe.message.assert_called_with('^7Admins online: Joe^7^7 [^3100^7], Mike^7^7 [^380^7]')


class Cmd_regulars(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)

    def test_no_regular(self):
        # only superadmin joe is connected
        self.joe.says('!regulars')
        self.joe.message.assert_called_with('^7There are no regular players online')

    def test_one_regular(self):
        # GIVEN
        self.mike.connects(1)
        self.joe.says('!makereg mike')
        # WHEN
        self.joe.says('!regs')
        # THEN
        self.joe.message.assert_called_with('^7Regular players online: Mike^7')

    def test_two_regulars(self):
        # GIVEN
        self.mike.connects(1)
        self.joe.says('!makereg mike')
        self.jack = FakeClient(self.console, name="Jack", guid="jackguid", groupBits=1)
        self.jack.connects(2)
        self.joe.says('!makereg jack')
        # WHEN
        self.joe.says('!regs')
        # THEN
        self.joe.message.assert_called_with('^7Regular players online: Mike^7, Jack^7')



class Cmd_map(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()

    def test_missing_param(self):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        self.joe.says('!map')
        self.joe.message.assert_called_once_with('^7You must supply a map to change to.')

    def test_suggestions(self):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        when(self.console).changeMap('f00').thenReturn(["bar1", "bar2", "bar3", "bar4", "bar5", "bar6", "bar7", "bar8", "bar9", "bar10", "bar11", "bar"])
        self.joe.says('!map f00')
        self.joe.message.assert_called_once_with('do you mean : bar1, bar2, bar3, bar4, bar5 ?')

    def test_nominal(self):
        self.joe.message = Mock(wraps=lambda x: sys.stdout.write("\t\t" + x + "\n"))
        self.joe.connects(0)
        when(self.console).changeMap('f00').thenReturn(None)
        self.joe.says('!map f00')
        self.assertEqual(0, self.joe.message.call_count)


class spell_checker(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.connects(0)

    def test_existing_command(self):
        self.joe.says('!map')
        self.assertEqual(['You must supply a map to change to.'], self.joe.message_history)

    def test_misspelled_command(self):
        self.joe.says('!mip')
        self.assertEqual(['Unrecognized command mip. Did you mean !map ?'], self.joe.message_history)

    def test_unrecognized_command(self):
        self.joe.says('!qfsmlkjazemlrkjazemrlkj')
        self.assertEqual(['Unrecognized command qfsmlkjazemlrkjazemrlkj'], self.joe.message_history)

    def test_existing_command_loud(self):
        self.joe.says('@map')
        self.assertEqual(['You must supply a map to change to.'], self.joe.message_history)

    def test_misspelled_command_loud(self):
        self.joe.says('@mip')
        self.assertEqual(['Unrecognized command mip. Did you mean @map ?'], self.joe.message_history)

    def test_unrecognized_command_loud(self):
        self.joe.says('@qfsmlkjazemlrkjazemrlkj')
        self.assertEqual(['Unrecognized command qfsmlkjazemlrkjazemrlkj'], self.joe.message_history)


class Cmd_register(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.p._commands = {}  # make sure to empty the commands list as _commands is a wrongly a class property
        self.say_patcher = patch.object(self.console, "say")
        self.say_mock = self.say_patcher.start()
        self.player = FakeClient(self.console, name="TestPlayer", guid="player_guid", groupBits=0)
        self.player.connects("0")

    def tearDown(self):
        Admin_functional_test.tearDown(self)
        self.say_patcher.stop()

    def test_nominal_with_defaults(self):
        # GIVEN
        self.init(r"""
        <configuration plugin="admin">
            <settings name="commands">
                <set name="register">guest</set>
            </settings>
            <settings name="messages">
                <set name="regme_annouce">%s put in group %s</set>
            </settings>
        </configuration>
        """)
        # WHEN
        self.player.says('!register')
        # THEN
        self.assertListEqual(['Thanks for your registration. You are now a member of the group User'],
                             self.player.message_history)
        self.assertListEqual([call('TestPlayer^7 put in group User')], self.say_mock.mock_calls)

    def test_custom_messages(self):
        # GIVEN
        self.init(r"""
        <configuration plugin="admin">
            <settings name="commands">
                <set name="register">guest</set>
            </settings>
            <settings name="settings">
                <set name="announce_registration">yes</set>
            </settings>
            <settings name="messages">
                <set name="regme_confirmation">You are now a member of the group %s</set>
                <set name="regme_annouce">%s is now a member of group %s</set>
            </settings>
        </configuration>
        """)
        # WHEN
        self.player.says('!register')
        # THEN
        self.assertListEqual(['You are now a member of the group User'], self.player.message_history)
        self.assertListEqual([call('TestPlayer^7 is now a member of group User')], self.say_mock.mock_calls)

    def test_no_announce(self):
        # GIVEN
        self.init(r"""
        <configuration plugin="admin">
            <settings name="commands">
                <set name="register">guest</set>
            </settings>
            <settings name="settings">
                <set name="announce_registration">no</set>
            </settings>
            <settings name="messages">
                <set name="regme_confirmation">You are now a member of the group %s</set>
                <set name="regme_annouce">%s is now a member of group %s</set>
            </settings>
        </configuration>
        """)
        # WHEN
        self.player.says('!register')
        # THEN
        self.assertListEqual(['You are now a member of the group User'], self.player.message_history)
        self.assertListEqual([], self.say_mock.mock_calls)


@patch("time.sleep")
class Cmd_spams(Admin_functional_test):

    def test_nominal(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="spams">20</set>
            </settings>
            <settings name="spamages">
                <set name="foo">foo</set>
                <set name="rule1">this is rule #1</set>
                <set name="rule2">this is rule #2</set>
                <set name="bar">bar</set>
            </settings>
        </configuration>""")
        self.joe.connects(0)
        # WHEN
        self.joe.says('!spams')
        # THEN
        self.assertListEqual(['Spamages: bar, foo, rule1, rule2'], self.joe.message_history)

    def test_no_spamage(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="spams">20</set>
            </settings>
            <settings name="spamages">
            </settings>
        </configuration>""")
        self.joe.connects(0)
        # WHEN
        self.joe.says('!spams')
        # THEN
        self.assertListEqual(['no spamage message defined'], self.joe.message_history)

    def test_reconfig_loads_new_spamages(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="spams">20</set>
            </settings>
            <settings name="spamages">
                <set name="foo">foo</set>
                <set name="rule1">this is rule #1</set>
            </settings>
        </configuration>""")
        self.joe.connects(0)
        self.joe.says('!spams')
        self.assertListEqual(['Spamages: foo, rule1'], self.joe.message_history)
        # WHEN
        self.conf.loadFromString(r"""<configuration>
            <settings name="commands">
                <set name="spams">20</set>
            </settings>
            <settings name="spamages">
                <set name="bar">bar</set>
                <set name="rule2">this is rule #2</set>
            </settings>
        </configuration>""")
        self.joe.says('!reconfig')
        self.joe.clearMessageHistory()
        self.joe.says('!spams')
        # THEN
        self.assertListEqual(['Spamages: bar, rule2'], self.joe.message_history)


@patch("time.sleep")
class Test_warn_command_abusers(Admin_functional_test):

    def setUp(self):
        Admin_functional_test.setUp(self)
        self.player = FakeClient(self.console, name="ThePlayer", guid="theplayerguid", groupBits=0)
        self.player_warn_patcher = patch.object(self.player, "warn")
        self.player_warn_mock = self.player_warn_patcher.start()

    def tearDown(self):
        Admin_functional_test.tearDown(self)
        self.player_warn_patcher.stop()

    def test_conf_empty(self, sleep_mock):
        # WHEN
        self.init(r"""<configuration>
            <settings name="commands">
            </settings>
            <settings name="warn">
            </settings>
        </configuration>""")
        # THEN
        self.assertFalse(self.p._warn_command_abusers)
        self.assertIsNone(self.p.getWarning("fakecmd"))
        self.assertIsNone(self.p.getWarning("nocmd"))

    def test_warn_reasons(self, sleep_mock):
        # WHEN
        self.init(r"""<configuration>
            <settings name="warn_reasons">
                <set name="fakecmd">1h, ^7do not use fake commands</set>
                <set name="nocmd">1h, ^7do not use commands that you do not have access to, try using !help</set>
            </settings>
        </configuration>""")
        # THEN
        self.assertTupleEqual((60.0, '^7do not use commands that you do not have access to, try using !help'),
                              self.p.getWarning("nocmd"))
        self.assertTupleEqual((60.0, '^7do not use fake commands'), self.p.getWarning("fakecmd"))

    def test_warn_no__no_sufficient_access(self, sleep_mock):
        # WHEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">2</set>
            </settings>
            <settings name="warn">
                <set name="warn_command_abusers">no</set>
            </settings>
        </configuration>""")
        self.assertFalse(self.p._warn_command_abusers)
        self.player.connects("0")
        # WHEN
        with patch.object(self.p, "info") as info_mock:
            self.player.says("!help")
        # THEN
        self.assertListEqual([call('ThePlayer does not have sufficient rights to use !help. Required level: 2')],
                             info_mock.mock_calls)
        self.assertListEqual([], self.player.message_history)
        self.assertFalse(self.player_warn_mock.called)

    def test_warn_yes__no_sufficient_access(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">2</set>
            </settings>
            <settings name="warn">
                <set name="warn_command_abusers">yes</set>
            </settings>
        </configuration>""")
        self.assertTrue(self.p._warn_command_abusers)
        self.player.connects("0")
        # WHEN
        with patch.object(self.p, "info") as info_mock:
            self.player.says("!help")
        # THEN
        self.assertListEqual([call('ThePlayer does not have sufficient rights to use !help. Required level: 2')],
                             info_mock.mock_calls)
        self.assertListEqual(['You do not have sufficient access to use !help'], self.player.message_history)
        self.assertFalse(self.player_warn_mock.called)

    def test_warn_yes__no_sufficient_access_abuser(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">2</set>
            </settings>
            <settings name="warn">
                <set name="warn_command_abusers">yes</set>
            </settings>
            <settings name="warn_reasons">
                <set name="nocmd">90s, do not use commands you do not have access to, try using !help</set>
            </settings>
        </configuration>""")
        self.player.connects("0")
        # WHEN
        with patch.object(self.p, "info") as info_mock:
            self.player.says("!help")
            self.player.says("!help")
            self.player.says("!help")
        # THEN
        self.assertListEqual([call('ThePlayer does not have sufficient rights to use !help. Required level: 2'),
                              call('ThePlayer does not have sufficient rights to use !help. Required level: 2')],
                             info_mock.mock_calls)
        self.assertListEqual(['You do not have sufficient access to use !help',
                              'You do not have sufficient access to use !help'], self.player.message_history)
        self.assertListEqual([call(1.5, 'do not use commands you do not have access to, try using !help',
                                   'nocmd', ANY, ANY)], self.player_warn_mock.mock_calls)


    def test_warn_no__unknown_cmd(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">0</set>
            </settings>
            <settings name="warn">
                <set name="warn_command_abusers">no</set>
            </settings>
        </configuration>""")
        self.assertFalse(self.p._warn_command_abusers)
        self.player.connects("0")
        # WHEN
        self.player.says("!hzlp")
        # THEN
        self.assertListEqual(['Unrecognized command hzlp. Did you mean !help ?'], self.player.message_history)
        self.assertFalse(self.player_warn_mock.called)

    def test_warn_yes__unknown_cmd(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">0</set>
            </settings>
            <settings name="warn">
                <set name="warn_command_abusers">yes</set>
            </settings>
        </configuration>""")
        self.assertTrue(self.p._warn_command_abusers)
        self.player.connects("0")
        # WHEN
        self.player.says("!hzlp")
        # THEN
        self.assertListEqual(['Unrecognized command hzlp. Did you mean !help ?'], self.player.message_history)
        self.assertFalse(self.player_warn_mock.called)

    def test_warn_yes__unknown_cmd_abuser(self, sleep_mock):
        # GIVEN
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">0</set>
            </settings>
            <settings name="warn">
                <set name="warn_command_abusers">yes</set>
            </settings>
            <settings name="warn_reasons">
                <set name="fakecmd">2h, do not use fake commands</set>
            </settings>
        </configuration>""")
        self.assertTrue(self.p._warn_command_abusers)
        self.player.connects("0")
        self.player.setvar(self.p, 'fakeCommand', 2)  # simulate already 2 use of the !help command
        # WHEN
        self.player.says("!hzlp")
        self.player.says("!hzlp")
        self.player.says("!hzlp")
        # THEN
        self.assertListEqual(['Unrecognized command hzlp. Did you mean !help ?',
                              'Unrecognized command hzlp. Did you mean !help ?',
                              'Unrecognized command hzlp. Did you mean !help ?'], self.player.message_history)
        self.assertListEqual([call(120.0, 'do not use fake commands', 'fakecmd', ANY, ANY)],
                             self.player_warn_mock.mock_calls)


@patch("time.sleep")
class Test_command_parsing(Admin_functional_test):

    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init(r"""<configuration>
            <settings name="commands">
                <set name="help">0</set>
            </settings>
        </configuration>""")
        self.joe.connects("0")

    def test_normal_chat(self, sleep_mock):
        # GIVEN
        self.joe.says("f00")
        self.assertListEqual([], self.joe.message_history)
        # WHEN
        self.joe.says("!help")
        # THEN
        self.assertListEqual(["Available commands: help, iamgod"], self.joe.message_history)

    def test_team_chat(self, sleep_mock):
        # GIVEN
        self.joe.says("f00")
        self.assertListEqual([], self.joe.message_history)
        # WHEN
        self.joe.says2team("!help")
        # THEN
        self.assertListEqual(["Available commands: help, iamgod"], self.joe.message_history)

    def test_squad_chat(self, sleep_mock):
        # GIVEN
        self.joe.says("f00")
        self.assertListEqual([], self.joe.message_history)
        # WHEN
        self.joe.says2squad("!help")
        # THEN
        self.assertListEqual(["Available commands: help, iamgod"], self.joe.message_history)

    def test_private_chat(self, sleep_mock):
        # GIVEN
        self.joe.says("f00")
        self.assertListEqual([], self.joe.message_history)
        # WHEN
        self.joe.says2private("!help")
        # THEN
        self.assertListEqual(["Available commands: help, iamgod"], self.joe.message_history)
