import socket
import time
import threading
from tabulate import tabulate
from datetime import datetime
import sys
import fcntl
import os
import selectors
class Router():
    def __init__ (self, ip='172.20.10.12', port=9000):
        self.router_table = {'ip_destino': [], 'metrica': [], 'ip_saida': []}
        self.ip = ip
        self.port = port
        self.receive_time = {}
        # socket para recebimento de mensagens
        self.l_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        self.l_sock.settimeout(2)
        self.l_sock.setblocking(0)
        self.l_sock.bind((self.ip, self.port))
        # socket para envio de mensagens
        self.s_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def _add_rout(self, dest_ip, metric, source_ip):
        """Adiciona uma rota na tabela de roteamento"""
        self.router_table['ip_destino'].append(dest_ip)
        self.router_table['metrica'].append(metric)
        self.router_table['ip_saida'].append(source_ip)
        print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nRota adicionada:\n   - Destino: {dest_ip}\n   - Métrica: {metric}\n   - Saída: {source_ip}\n")

    def _read_file(self, filepath):
        """Lê o arquivo e adiciona as rotas iniciais"""
        with open(filepath, 'r') as file:
            rotas = file.readlines()
        for r in rotas:
            r = r.strip()
            if r:
                self._add_rout(r, 1, r)
        self._print_router_table()

    def _get_index(self, dest_ip):
        """Obtém o índice de uma rota na tabela com base no IP de destino"""
        return self.router_table['ip_destino'].index(dest_ip)   
        
    def _check_inactive_routes(self):
        """Remove rotas inativas após 35 segundos"""
        current_time = time.time()
        inactive = [ip for ip, last_time in self.receive_time.items() if (current_time - last_time) > 35]
        for ip in inactive:
            self._delete_ips_from_inactive_routes(ip)
            self.receive_time = {ip: time for ip, time in self.receive_time.items() if ip != ip}
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rota inativa removida: {ip}\n")
            self._print_router_table()
                
    def _delete_ips_from_inactive_routes(self, remove_ip):
        """Remove rotas com IP de saída inativo"""
        idx = [idx for idx, _ in enumerate(self.router_table['ip_destino']) if self.router_table['ip_saida'][idx] == remove_ip]
        for i in idx:
            self.router_table = {
                    'ip_destino': [dest for dest, saida in zip(self.router_table['ip_destino'], self.router_table['ip_saida']) if saida != remove_ip],
                    'metrica': [metrica for metrica, saida in zip(self.router_table['metrica'], self.router_table['ip_saida']) if saida != remove_ip],
                    'ip_saida': [saida for saida in self.router_table['ip_saida'] if saida != remove_ip]
            }
    
    def _send_router_table(self): 
        """Envia a tabela de roteamento para todos os IPs de destino"""
        try:
            message = ''.join([
                f"@{ip_dest}-{met}" 
                for ip_dest, met in zip(self.router_table['ip_destino'], self.router_table['metrica'])
            ])
            for ip in self.router_table['ip_destino']:
                self.s_sock.sendto(message.encode(), (ip, self.port))
                print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tabela de roteamento enviada para: {ip}\n")
        except:
            print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao mandar a tabela de roteamento\n")
    
    def _send_message(self,message,ip):
        """Envia uma mensagem para todos os IPs de destino"""
        try:
            idx = self._get_index(ip)
            message = f'!{self.ip};{ip};{message}'
            self.s_sock.sendto(message.encode(), (self.router_table['ip_saida'][idx], self.port))
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nMensagem enviada para: {ip}\n   - Conteúdo: '{message}'\n")
        except:
            print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao mandar a mensagem: {message}\n")

            
    def _receive_router_table(self, routers, addr):
        """Recebe mensagens de roteadores vizinhos e atualiza a tabela de roteamento"""
        routers = routers.split('@')[1:]
        for rout in routers:
            info = rout.split('-')
            if len(info) < 2:
                continue
            dest_ip, metric = info[0], int(info[1])
            metric += 1
            if dest_ip == self.ip:
                continue
            if dest_ip not in self.router_table['ip_destino']:
                self._add_rout(dest_ip, metric, addr[0])
                self._send_router_table()
                print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rota nova detectada e adicionada pela atualização: {dest_ip}\n")
                self._print_router_table()
            elif dest_ip in self.router_table['ip_destino']:
                index = self._get_index(dest_ip)
                if metric < self.router_table['metrica'][index]:
                    self.router_table['ip_saida'][index] = addr[0]
                    self.router_table['metrica'][index] = metric
                    print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rota existente atualizada: {dest_ip}\n")
                    self._print_router_table()
    
    def _read_message(self, message_ori, ip_ori):
        split_message = message_ori.split(';')
        ip_dest, message = split_message[1], split_message[-1]
        if ip_dest == self.ip:
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mensagem recebida de {ip_ori}:\n   - '{message}'\n")
        else:
            idx = self._get_index(ip_dest)
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Repassando a mensagem de {ip_ori}\n")
            self.l_sock.sendto(message_ori.encode(),(self.router_table["ip_saida"][idx],self.port))
            self.l_sock.sendto(message_ori.encode(),(self.router_table["ip_saida"][idx],self.port))

    def _print_router_table(self):
        """Imprime a tabela de roteamento em formato tabular"""
        headers = ["IP Destino", "Métrica", "IP Saída"]
        table_data = zip(self.router_table['ip_destino'], 
                        self.router_table['metrica'], 
                        self.router_table['ip_saida'])
        
        print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tabela de Roteamento:\n")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def _new_router(self, dest_ip, metric, source_ip):
        """Adiciona um novo roteador na tabela de roteamento"""
        print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mensagem de entrada na rede recebida de: {dest_ip}\n")
        if dest_ip not in self.router_table['ip_destino']:
            self._add_rout(dest_ip, metric, source_ip)
            self._send_router_table()
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rota nova detectada e adicionada: {dest_ip}\n")
            self._print_router_table()
        else:
            print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Rota já existente: {dest_ip}\n")

    def _handle_keyboard_input(self, stdin):
        """Detecta se algo foi enviado no terminal."""
        user_input = stdin.read().strip()
        if user_input:
            if user_input.startswith('!'):
                try:
                    split_message = user_input.split(';')
                    dest, message = split_message[0][1:], split_message[1]
                    self._send_message(message, dest)
                except:
                    print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao mandar a mensagem: {message}\n")
            else: 
                print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mensagem fora do padrão: {user_input}\n")

    def listen(self):
        """Escuta por mensagens de outros roteadores"""
        while True:
            self._check_inactive_routes()
            try:
                data, addr = self.l_sock.recvfrom(1024)
            except socket.timeout:
                continue
            except BlockingIOError:
                continue
            self.receive_time[addr[0]] = time.time()
            data = data.decode()
            if data.startswith('@'):
                self._receive_router_table(data, addr)
            elif data.startswith('!'):
                self._read_message(data, addr[0])
            elif data.startswith('*'):
                self._new_router(addr[0], 1, addr[0])
            else:
                print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Prefixo desconhecido: {data[0]}\n")
    
    def sender(self):
        """Envia mensagens para outros roteadores e monitora entrada do teclado."""
        # https://stackoverflow.com/questions/21791621/taking-input-from-sys-stdin-non-blocking
        # set sys.stdin non-blocking
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)
        
        # Create a selector and register sys.stdin for keyboard input events
        m_selector = selectors.DefaultSelector()
        m_selector.register(sys.stdin, selectors.EVENT_READ, self._handle_keyboard_input)

        last_print_router_table = time.time()
        last_send_router_table = time.time()

        while True:
            # Print the router table every 30 seconds
            if time.time() - last_print_router_table > 30:
                self._print_router_table()
                last_print_router_table = time.time()
            
            # Send the router table every 15 seconds
            if time.time() - last_send_router_table > 15:
                self._send_router_table()
                last_send_router_table = time.time()
            
            # Check for keyboard input events
            for k, mask in m_selector.select(timeout = 0.1):
                callback = k.data # Retrieves _handle_keyboard_input, which was stored as the callback when the selector was registered 
                callback(k.fileobj) # Calls _handle_keyboard_input, passing k.fileobj (which is sys.stdin) as an argument to the function

    def starter(self, filepath):
        self._read_file(filepath)
        message = f'*{self.ip}'
        self._send_router_table()
        for ip in self.router_table['ip_destino']:
            self.s_sock.sendto(message.encode(), (ip, self.port))
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mensagem de entrada na rede enviada para: {ip}\n")


if __name__ == '__main__':
    router = Router()
    router.starter('roteadores.txt')
    listener_thread = threading.Thread(target=router.listen)
    listener_thread.start()
    sender_thread = threading.Thread(target=router.sender)
    sender_thread.start()
