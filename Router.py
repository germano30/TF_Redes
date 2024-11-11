import socket
import time
import threading
from tabulate import tabulate
from datetime import datetime

class Router():
    def __init__ (self, ip='172.20.10.11', port=9000):
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
        message = ''.join([
            f"@{ip_dest}-{met}" 
            for ip_dest, met in zip(self.router_table['ip_destino'], self.router_table['metrica'])
        ])
        for ip in self.router_table['ip_destino']:
            self.s_sock.sendto(message.encode(), (ip, self.port))
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Tabela de roteamento enviada para: {ip}\n")
    
    def _send_message(self):
        """Envia uma mensagem para todos os IPs de destino"""
        for ip in self.router_table['ip_destino']:
            message = f'!{self.ip};{ip};Oi tudo bem?'
            self.s_sock.sendto(message.encode(), (ip, self.port))
            print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\nMensagem enviada para: {ip}\n   - Conteúdo: '{message}'\n")
            
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
    
    def _print_message(self, message, ip_ori):
        message = message.split(';')[-1]
        print(f"\n[INFO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mensagem recebida de {ip_ori}:\n   - '{message}'\n")
 
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
                self._print_message(data, addr[0])
            elif data.startswith('*'):
                self._new_router(addr[0], 1, addr[0])
            else:
                print(f"\n[AVISO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Prefixo desconhecido: {data[0]}\n")
    
    def sender(self):
        """Envia mensagens para outros roteadores"""
        last_print_router_table = time.time()
        while True:
            if time.time() - last_print_router_table > 20:
                self._print_router_table()
                last_print_router_table = time.time()
            self._send_router_table()
            time.sleep(5)
            self._send_message()
            time.sleep(10)
    
    def starter(self, filepath):
        self._read_file(filepath)
        message = f'*{self.ip}'
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
