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
import paramiko
import os
import socket
import cgi
import traceback
import random
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
    hosts   -- Host dict of tuples with password (or login:password in case of ssh),
                host address, port number, type (SSH == int(1) or TELNET == int(0))
                and name for display (default not set)

    ipv4_disable    -- Disable ipv4 resolving and check of arguments
                        (default False)
    ipv6_disable    -- Disable ipv6 resolving and check of arguments
                        (default False)
    resolve         -- Resolve hostnames (default True)
    """
    name = None
    cmds = None
    hosts = None
    ipv4_disable = False
    ipv6_disable = False
    resolve = True

    def __init__(self, **kwargs):
        for i in ['name', 'cmds', 'hosts']:
            if not i in self.__dict__ or not self.__dict__[i]:
                setattr(self, i, kwargs[i])
            assrt(self.__dict__[i], "%s is not set" % i)
        assrt(isinstance(self.name, (str, unicode)),
              "%r is not string or unicode" % self.name)
        assrt(isinstance(self.cmds, dict), "%r is not dict" % self.cmds)
        for d in self.cmds.values():
            for i in d.values():
                assrt(isinstance(i, (str, unicode)),
                      "%r is not string or unicode" % i)
        assrt(isinstance(self.hosts, dict), "%r is not dict" % self.hosts)
        for d in self.hosts.values():
            assrt(isinstance(d, tuple), "%r is not tuple" % d)
            assrt(len(d) == 6, "%r length is not 6" % d)
            assrt(isinstance(d[0], (str, unicode)),
                  "%r is not string or unicode" % d[0])
            assrt(isinstance(d[1], str), "%r is not string" % d[1])
            assrt(isinstance(d[2], int), "%r is not integer" % d[2])
            assrt(d[3] in (TELNET, SSH), "%r is not TELNET or SSH type" % d[3])
            assrt(isinstance(d[4], (str, unicode)),
                  "%r is not string or unicode" % d[4])
            assrt(isinstance(d[5], (str, unicode)),
                  "%r is not string or unicode" % d[5])

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
        if "%ARG%" in command:
            if self.__is_ipv4(arg) or self.__is_ipv6(arg):
                command = command.replace("%ARG%", arg)
            elif self.resolve:  # Hostname support
                try:
                    socket.setdefaulttimeout(5)
                    arg = random.choice(socket.getaddrinfo(arg, None))[4][0]
                    command = command.replace("%ARG%", arg)
                except:
                    traceback.print_exc()
                    raise ValueError
            else:
                raise AttributeError
        if typ == TELNET:
            tn = telnetlib.Telnet(host, port)
            if pwd:
                tn.read_until("Password: ", 5)  # 5 seconds timeout
                tn.write(pwd + "\n")
            tn.write(str(command) + "\n")  # sanitize arguments!?
            try:
                tn.write("exit\n")
            except:
                pass
            read_data = str(tn.read_all()).splitlines()
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
        if 'exit' in read_data[-1]:
            read_data.pop(-1)
        for line in read_data:
            if command not in line:
                pre_return.append(line)
        return str(os.linesep.join(pre_return)).strip()

    def template(self, *args):
        assrt(len(args) == 2, "%r length is not 2" % args)
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
                                      v[3],
                                      '</option>'])
                             for k, v in enumerate(self.hosts)])
            commands = "".join(["".join(['<option value="',
                                         str(k),
                                         '">',
                                         k,
                                         '</option>'])
                                for k in self.cmds[self.hosts[0].keys()])  # First taken as all profiles must have same data
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

if __name__ == '__main__':
    import argparse

    def tuples(s):
        try:
            password, ip, port, conn, name, profile = map(
                unicode, s.split(','))
            return unicode(password), str(ip), int(port), int(conn), unicode(name), unicode(profile)
        except:
            raise argparse.ArgumentTypeError("""Hosts must be 'password' (or for ssh 'login:password'),'ip',port,'name','profile'
    password, ip, name and profile == string or unicode and port, conn == int""")
    parser = argparse.ArgumentParser()
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
                        type=dict,
                        default={},
                        nargs='*',
                        action="append",
                        help="Commands dict of dict for profiles where key is profile name, use %%ARG%% for substition of IP/hostname argument. Key in command is display friendly version",
                        required=False)
    parser.add_argument("-H",
                        "--hosts",
                        dest='hosts',
                        type=tuples,
                        nargs='*',
                        help="Host list of tuples with password, host address, port number, type of connection (ssh or telnet), name for display and command profile to use",
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
    else:
        commands = {
            'cisco': {
                'BGP Summary': 'sh ip bgp summary',
                'BGP Advertised _ARGUMENT_ to Neighbor': 'sh ip bgp neighbor %ARG% advertised',
                'Ping': 'ping %ARG%',
                'Traceroute': 'traceroute %ARG%'
            },
            'juniper': {
                'BGP Summary': 'echo "sh bgp sum" | cli',
                'BGP Advertised _ARGUMENT_ to Neighbor': 'echo "show route advertising-protocol bgp %ARG%" | cli',
                'Ping': 'ping -c 4 %ARG%',
                'Traceroute': 'traceroute %ARG%'
            }
        }
    if a.hosts:
        hosts = a.hosts
    else:
        hosts = [("password1", "192.168.0.1", 23, TELNET, "Cisco", 'cisco'),
                 ("password2", "192.168.1.1", 2605, TELNET, "Quagga", 'cisco'),
                 ("login:password3", "192.168.2.1", 22, SSH, "Juniper", 'juniper')]
    httpd = make_server(a.bind, a.port, lookingglass(
        name=a.name, cmds=commands, hosts=hosts))
    httpd.serve_forever()
