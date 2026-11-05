"""Reject external sockets in the integration verification subprocess only."""
import socket
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_getaddrinfo = socket.getaddrinfo

def permitted(address):
    return isinstance(address, str) or address[0] in ('127.0.0.1', '::1', 'localhost')

def connect(self, address):
    if not permitted(address):
        raise RuntimeError('integration_offline_external_network_forbidden')
    return _original_connect(self, address)

def connect_ex(self, address):
    if not permitted(address):
        raise RuntimeError('integration_offline_external_network_forbidden')
    return _original_connect_ex(self, address)

def getaddrinfo(host, *args, **kwargs):
    if host not in (None, 'localhost', '127.0.0.1', '::1'):
        raise RuntimeError('integration_offline_external_dns_forbidden')
    return _original_getaddrinfo(host, *args, **kwargs)

socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
socket.getaddrinfo = getaddrinfo
