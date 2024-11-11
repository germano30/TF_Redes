import socket
import time 
import threading

class Router():
    def __init__ (self, ip = '127.0.0.1', port = 9000):
        self.router_table = {'ip_destino': [], 'metrica': [], 'ip_saida': []}
        self.ip = ip
        self.port = port
        self.receive_time = {}
        self.l_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.w_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        
    
    def _add_rout(self, dest_ip, metric, source_ip):
        """Adiciona uma rota na tabela de roteamento"""
        self.router_table['ip_destino'].append(dest_ip)
        self.router_table['metrica'].append(metric)
        self.router_table['ip_saida'].append(source_ip)
    
    def _read_file(self,filepath):
        """Lê o arquivo e adiciona as rotas iniciais"""
        with open(filepath, 'r') as file:
            rotas = file.readlines() 

        for r in rotas:
            r = r.strip()
            if r:
                self._add_rout(r, 1, r)

    def _get_index(self, dest_ip):
        """Obtém o índice de uma rota na tabela com base no IP de destino"""
        return self.router_table['ip_destino'].index(dest_ip)   
        
    def _check_inactive_routes(self):
        """Remove rotas inativas após 35 segundos"""
        while True:
            current_time = time.time()
            inactive = [ip for ip, last_time in self.receive_time.items() if (last_time - current_time) > 35]
            for ip in inactive:
                self._delete_ips_from_inactive_routes(ip)
                del self.receive_time[ip]
            time.sleep(5)
                
    def _delete_ips_from_inactive_routes(self, remove_ip):
        """Remove rotas com IP de saída inativo"""
        idx = [idx for idx, _ in enumerate(self.router_table['ip_destino']) if self.router_table['ip_saida'][idx] == remove_ip]
        for i in idx:
            del self.router_table['ip_destino'][i]
            del self.router_table['metrica'][i]
            del self.router_table['ip_saida'][i]
            
    def _send_router_table(self): 
        """Envia a tabela de roteamento para todos os IPs de destino"""
        message = ''.join([
            f"@{ip_dest}-{met}" 
            for ip_dest, met in zip(self.router_table['ip_destino'], self.router_table['metrica'])
        ])
        for ip in self.router_table['ip_destino']:
            self.w_sock.sendto(message.encode(), (ip, self.port))
            print(f'---> Tabela de roteamento enviada para: {ip}') 
    
    def _send_message(self):
        """Envia uma mensagem para todos os IPs de destino"""
        for ip in self.router_table['ip_destino']:
            message = f'!{self.ip};{ip};Oi tudo bem?'
            self.w_sock.sendto(message.encode(), (ip, self.port))
            print(f'---> Mensagem enviada para: {ip}')
            
    def _receive_router_table(self, routers, addr):
        """Recebe mensagens de roteadores vizinhos e atualiza a tabela de roteamento"""
        routers = routers.split('@')[1:]
        for rout in routers:
            info = rout.split('-')
            if len(info) < 2:
                continue
            dest_ip, metric = info[0], int(info[1])
            metric += 1
            if dest_ip not in self.router_table['ip_destino']:
                self._add_rout(dest_ip, metric, addr[0])
                self._send_router_table()
            elif dest_ip in self.router_table['ip_destino']:
                index = self._get_index(dest_ip)
                if metric < self.router_table['metrica'][index]:
                    self.router_table['ip_saida'][index] = addr[0]
                    self.router_table['metrica'][index] = metric
    
    def _print_message(self,message, ip_ori):
        message = message.split(';')[-1]
        print(f'---> Mensagem recebia de {ip_ori}: {message}')
        
    def listen(self):
        """Escuta por mensagens de outros roteadores"""
        self.l_sock.bind((self.ip, self.port))
        while True:
            data, addr = self.l_sock.recvfrom(1024)
            if not data:
                continue
            self.receive_time[addr[0]] = time.time()
            data = data.decode()
            if data.startswith('@'):
                self._receive_router_table(data, addr)
            elif data.startswith('!'):
                self._print_message(data,addr[0])
            elif data.startswith('*'):
                pass  # TODO adicionar o tratamento para mensagens de controle
            else:
                print(f'Prefixo fora do padrão - {data[0]}')
    
    def sender(self):
        """Envia mensagens para outros roteadores"""
        while True:
            self._send_router_table()
            time.sleep(5)
            self._send_message()
            time.sleep(10)
    
    def starter(self,filepath):
        self._read_file(filepath)
        message = f'*{self.ip}'
        for ip in self.router_table['ip_destino']:
            self.w_sock.sendto(message.encode(), (ip, self.port))

if __name__ == '__main__':
    router = Router()
    router.starter('roteadores.txt')
    listener_thread = threading.Thread(target=router.listen)
    listener_thread.start()
    sender_thread = threading.Thread(target=router.sender)
    sender_thread.start()