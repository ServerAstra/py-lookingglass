#!/usr/bin/env python
# coding=utf8
"""
Copyright (c) 2012-2015 ServerAstra Ltd.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import telnetlib
try:
    import paramiko
    NOSSH = 0
except ImportError:
    NOSSH = 1
import os
import socket
import cgi
import traceback
import random
import json  # For config
import os.path
from time import sleep
from wsgiref.simple_server import make_server


TELNET = 0
SSH = 1


def assrt(check, error=None):
    if check:
        return 1
    else:
        if error:
            raise AssertionError(error)
        raise AssertionError


class lookingglass(object):

    """lookingglass object

    Keyword arguments:
    name    -- Header name for pages (default not set)
    cmds    -- Commands dict of dicts, use %ARG% for substition of IP or hostname
                argument (default not set)
    hosts   -- Host list of tuples with password (or login:password in case of ssh),
                host address, port number, type (SSH == int(1) or TELNET == int(0))
                and name for display (default not set)

    ipv4_disable    -- Disable ipv4 resolving and check of arguments
                        (default False)
    ipv6_disable    -- Disable ipv6 resolving and check of arguments
                        (default False)
    resolve         -- Resolve hostnames (default False)
    """
    name = None
    cmds = None
    hosts = None
    ipv4_disable = False
    ipv6_disable = False
    resolve = False

    def __init__(self, **kwargs):
        for i in ['name', 'cmds', 'hosts']:
            if not i in self.__dict__ or not self.__dict__[i]:
                setattr(self, i, kwargs[i])
            assrt(self.__dict__[i], "%s is not set".format(i))
        assrt(isinstance(self.name, (str, unicode)),
              "{0!r} is not string or unicode".format(self.name))
        assrt(isinstance(self.cmds, dict),
              "{0!r} is not dict".format(self.cmds))
        for d in self.cmds.values():
            for i in d.values():
                assrt(isinstance(i, (str, unicode)),
                      "{0!r} is not string or unicode".format(i))
        assrt(isinstance(self.hosts, list),
              "{0!r} is not list".format(self.hosts))
        for d in self.hosts:
            assrt(isinstance(d, tuple), "{0!r} is not tuple".format(d))
            assrt(len(d) == 6, "{0!r} length is not 6".format(d))
            assrt(isinstance(d[0], (str, unicode)),
                  "{0!r} is not string or unicode".format(d[0]))
            assrt(isinstance(d[1], str), "{0!r} is not string".format(d[1]))
            assrt(isinstance(d[2], int), "{0!r} is not integer".format(d[2]))
            assrt(d[3] in (TELNET, SSH),
                  "{0!r} is not TELNET or SSH type".format(d[3]))
            assrt(isinstance(d[4], (str, unicode)),
                  "{0!r} is not string or unicode".format(d[4]))
            assrt(isinstance(d[5], (str, unicode)),
                  "{0!r} is not string or unicode".format(d[5]))

    def __is_ipv4(self, address):
        # Thanks tzot @ stackoverflow.com
        if self.ipv4_disable:
            return False
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except socket.error:
                return False
            return address.count('.') == 3
        except socket.error:  # not a valid address
            return False
        return True

    def __is_ipv6(self, address):
        # Thanks tzot @ stackoverflow.com
        if self.ipv6_disable:
            return False
        try:
            socket.inet_pton(socket.AF_INET6, address)
        except socket.error:  # not a valid address
            return False
        return True

    def __issuecommand(self, host, port, typ, pwd, command, arg):
        socket.setdefaulttimeout(30)
        if "%ARG%" in command:
            if self.__is_ipv4(arg) or self.__is_ipv6(arg):  # Not IPv4 or IPv6
                command = command.replace("%ARG%", arg)
            elif len(socket.getaddrinfo(arg, None)) > 0 and not self.resolve:
                # Resolve by switch/router
                command = command.replace("%ARG%", arg)
            elif self.resolve:  # Hostname support
                try:
                    arg = random.choice(socket.getaddrinfo(arg, None))[4][0]
                    command = command.replace("%ARG%", arg)
                except:
                    traceback.print_exc()
                    raise ValueError
            else:
                raise AttributeError
        if typ == TELNET:
            try:
                tn = telnetlib.Telnet(host, port, timeout=30)
                if pwd:
                    tn.read_until("Password: ", 30)  # 30 seconds timeout
                    tn.write(str(pwd) + "\r\n")
                p = ""
                timer = 50  # 5 seconds read timeout
                while timer:
                    if tn.sock_avail():
                        p += tn.read_some()
                        timer += 1
                    else:
                        timer -= 1
                        sleep(0.1)
                prompt = p.splitlines()[-1]  # Last line with prompt
                tn.write(str(command) + "\r\n")  # Sanitize arguments!?
                read_data = tn.read_until(prompt, 10)
                read_data = read_data.splitlines()
                for line in read_data[:]:
                    if prompt in line:
                        read_data.remove(line)
                tn.write("exit\r\n")
                tn.close()
            except socket.timeout:
                read_data = ['Connection Timeout, please try again later']
        elif typ == SSH:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                host, port, username=pwd.split(':')[0], password=pwd.split(':')[1])
            stdin, stdout, stderr = ssh.exec_command(
                str(command))  # sanitize arguments!!??
            read_data = stdout.read().splitlines()
            ssh.close()
        pre_return = []
        indexes = [0, len(read_data)]
        for line in read_data:
            if command in line:
                indexes[0] = read_data.index(line) + 1
            elif 'exit' in line:
                indexes[1] = read_data.index(line)
        pre_return = read_data[indexes[0]: indexes[1]]
        return str(os.linesep.join(pre_return)).strip()

    def template(self, *args):
        assrt(len(args) == 2, "{0!r} length is not 2".format(args))
        return """
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <title>{}</title>
                    <meta name="description" content="">
                    <meta name="author" content="">
                </head>
                <body>
                    {}
                </body>
            </html>
            """.format(*args)

    def __call__(self, env, respond):
        header = [('Server', 'py-LookingGlass'), ('Content-Type', 'text/html')]
        data = [self.name, '<h1>Not Found</h1>']
        status = '404 Not found'
        if env['PATH_INFO'] == "/":
            status = '200 OK'
            output = ""
            if env['REQUEST_METHOD'] == "POST":
                post_env = env.copy()
                post_env['QUERY_STRING'] = ''
                post = cgi.FieldStorage(
                    fp=env['wsgi.input'],
                    environ=post_env,
                    keep_blank_values=True
                )
                if "host" in post and "command" in post and "args" in post:
                    try:
                        output = self.__issuecommand(
                            self.hosts[int(post.getfirst('host'))][1],
                            self.hosts[int(post.getfirst('host'))][2],
                            self.hosts[int(post.getfirst('host'))][3],
                            self.hosts[int(post.getfirst('host'))][0],
                            self.cmds[self.hosts[int(post.getfirst('host'))][5]][
                                str(post.getfirst('command'))],
                            post.getfirst('args'))
                    except ValueError:
                        output = "Invalid Argument"
                        traceback.print_exc()
                    except AttributeError:
                        output = "Arguments are disabled"
                        traceback.print_exc()
            hosts = "".join(["".join(['<option value="',
                                      str(k),
                                      '">',
                                      v[4],
                                      '</option>'])
                             for k, v in enumerate(self.hosts)])
            commands = "".join(["".join(['<option value="',
                                         str(k),
                                         '">',
                                         str(k),
                                         '</option>'])
                                for k in self.cmds[self.hosts[0][-1]].keys()])  # First taken as all profiles must have same data
            data = [self.name, """
            <section>
            <header>Looking Glass</header><br>
            <form method="POST">
                <label>Router:&nbsp;</label><select name="host">"""
                    + hosts + """</select>
                <label>Type:&nbsp;</label><select name="command">"""
                    + commands + """</select>
                <label>Argument:&nbsp;</label><input type="text" name="args"/><br>
                <label>Output:&nbsp;</label><br><textarea style="width:100%;height:400px">"""
                    + output + """</textarea><br>
                <button type="submit" name="submit" value="Go">Go</button>
            </form>
            </section>"""]
        response = self.template(*data)
        header.append(('Content-Length', str(len(response))))
        respond(status, header)
        return [response]


def main():
    import argparse
    commands = {
        'cisco': {
            'BGP Summary': 'sh ip bgp summary',
            'BGP Advertised _ARGUMENT_ to Neighbor': 'sh ip bgp neighbor %ARG% advertised',
            'Ping': 'ping %ARG%',
            'Traceroute': 'traceroute %ARG%'
        },
        'juniper': {
            'BGP Summary': 'cli -c "sh bgp sum"',
            'BGP Advertised _ARGUMENT_ to Neighbor': 'cli -c "show route advertising-protocol bgp %ARG%"',
            'Ping': 'ping -c 4 %ARG%',
            'Traceroute': 'traceroute %ARG%'
        }
    }

    def tuples(s):
        try:
            password, ip, port, conn, name, profile = map(
                unicode, s.split(','))
            return unicode(password), str(ip), int(port), int(conn), unicode(name), unicode(profile)
        except:
            raise argparse.ArgumentTypeError("""Hosts must be 'password' (or for ssh 'login:password'),'ip',port,'name','profile'
    password, ip, name and profile == string or unicode and port, conn == int""")
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-n",
                        "--name",
                        dest='name',
                        type=str,
                        default='Looking Glass',
                        help="Header name for pages",
                        required=False)
    parser.add_argument("-c",
                        "--commands",
                        dest='commands',
                        type=json.loads,
                        default={},
                        nargs='*',
                        action="append",
                        help="Json array for profiles where key is profile name, use %%ARG%% for substition of IP/hostname argument. Key in command is display friendly version. \r\n Example: \r\n" +
                        json.dumps(commands, indent=2).replace('%', '%%'),
                        required=False)
    parser.add_argument("-H",
                        "--hosts",
                        dest='hosts',
                        type=tuples,
                        nargs='*',
                        help="Comma separated profile for router 'password','host_address',port_number,type_of_connection(1 for ssh and 0 for telnet),name,command_profile separated by space. \r\n Example \r\n" +
                        '"password1","192.168.0.1",23,0,"Cisco","cisco" "login:password2","192.168.1.1",22,0,"Juniper","juniper"',
                        required=False)
    parser.add_argument("-b",
                        "--bind",
                        type=str,
                        dest='bind',
                        default='localhost',
                        help="IP to bind",
                        required=False)
    parser.add_argument("-p",
                        "--port",
                        type=int,
                        dest='port',
                        default=8000,
                        help="port to bind",
                        required=False)
    a = parser.parse_args()
    if a.commands:
        commands = a.commands

    if a.hosts:
        hosts = a.hosts
    else:
        hosts = [("password1", "192.168.0.1", 23, TELNET, "Cisco", 'cisco'),
                 ("password2", "192.168.1.1", 2605, TELNET, "Quagga", 'cisco'),
                 ("login:password3", "192.168.2.1", 22, SSH, "Juniper", 'juniper')]

    if NOSSH:
        hosts = [i for i in hosts if i[3] != SSH]
    httpd = make_server(a.bind, a.port, lookingglass(
        name=a.name, cmds=commands, hosts=hosts, resolve=False))
    httpd.serve_forever()


if __name__ == '__main__':
    main()
