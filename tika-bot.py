#! /usr/bin/env python
# vim: set fileencoding=utf-8 sw=4 sts=4 expandtab:
#
# Simple IRC bot to receive notifications through XML-RCP and display them in a
# channel.
#
# © Matthijs Kooijman <matthijs@stdin.nl>
# Based on an example by Joel Rosdahl <joel@rosdahl.net>

"""Notification IRC Bot

This is a simple bot that joins a channel and then waits for notifications to
be pushed through XML-RPC. These notifications will then be displayed in the
proper channel.

The known commands are:

    stats -- Prints some channel information.

    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.

    die -- Let the bot cease to exist.
"""

import irc.bot
from irc.client import irc_lower, ip_numstr_to_quad, ip_quad_to_numstr

import pwd
import grp
import xmlrpc
import daemon
import daemon.pidlockfile
import optparse

class TikaBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments()[0])

    def on_pubmsg(self, c, e):
        a = e.arguments()[0].split(":", 1)
        if len(a) > 1 and irc_lower(a[0]) == irc_lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def do_command(self, e, cmd):
        nick = e.source()
        c = self.connection

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = chobj.users()
                users.sort()
                c.notice(nick, "Users: " + ", ".join(users))
                opers = chobj.opers()
                opers.sort()
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = chobj.voiced()
                voiced.sort()
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        else:
            c.notice(nick, "Not understood: " + cmd)

    def say(self, s):
        self.connection.privmsg(self.channel, s)

def main():
    parser = optparse.OptionParser(usage="usage: %prog [options] server[:port] channel")

    parser.add_option("--nick", action="store", dest="nick",
                      help="the IRC nick to use (default: %default)",
                      default="tika-bot")

    parser.add_option("-f", "--foreground", action="store_true", dest="foreground",
                      help="don't daemonize, run in the foreground instead")

    parser.add_option("-u", "--user", action="store", dest="user",
                      help="the user to run as (default: the current user)")

    parser.add_option("-g", "--group", action="store", dest="group",
                      help="the group to run as (default: the primary group of the user passed to --user, or the current group if --user is not given)")

    parser.add_option("-p", "--use-pidfile", action="store_true", dest="use_pidfile",
                      help="create a pidfile on startup on remove it again on shutdown")

    parser.add_option("--pidfile", action="store", dest="pidfile",
                      metavar="FILE", default="/var/run/tika-bot.pid",
                      help="the location of the pidfile")

    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.error("Not enough arguments provided")

    s = args[0].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print "Error: Erroneous port."
            sys.exit(1)
    else:
        port = 6667
    channel = args[1]

    uid = None
    gid = None
    if options.user:
        try:
            entry = pwd.getpwnam(options.user)
            uid = entry.pw_uid
            gid = entry.pw_gid
        except KeyError, e:
            parser.error("User not found: %s" % options.user)
    if options.group:
        try:
            gid = grp.getgrnam(options.group).gr_gid
        except KeyError, e:
            parser.error("Group not found: %s" % options.group)


    bot = TikaBot(channel, options.nick, server, port)

    # This spawns a new thread (that will automatically quit when the
    # main thread quits). Note that no attempt is made to do locking at this
    # moment, so it seems there's a chance that both threads are going to send
    # a command at the same time, with all kinds of odd side effects. But, how
    # likely is that?
    rpc = xmlrpc.XMLRPC(bot)
    rpc.daemon = True
    rpc.start()

    if options.foreground:
        bot.start()
    else:
        if options.use_pidfile:
            pidcontext = daemon.pidlockfile.PIDLockFile(options.pidfile)    
        else:
            pidcontext = None

        # Daemonize
        with daemon.DaemonContext(uid=uid, gid=gid, pidfile=pidcontext):
            bot.start()

    # bot.start() never returns

if __name__ == "__main__":
    main()
