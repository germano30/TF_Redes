import socket
import time 

class Router():
    def __init__ (self, ip, port = 9000):
        self._router_table = {'ip_destino': [], 'metrica': [], 'ip_saida': []}
        self._ip = ip
        self._port = port
        self._receive_time = {}
    
    def _add_rout(self,source_ip, metric, dest_ip):
        self._router_table['ip_destino'].append(source_ip)
        self._router_table['metrica'].append(metric)
        self._router_table['ip_saida'].append(dest_ip)
    
    def _read_file(self,filepath):
        #{ip_destino: x, metrica: x, ip_saida: x}
        file = open (filepath, 'r')
        rotas = file.readlines()
        file.close()
        for r in rotas:
            data = r.split(',')
            self._add_rout(data[0],1,data[1])
            
    def _check_inactive_routes(self):
        while True:
            current_time = time.time()
            inactive = [ip for ip, last_time in self._receive_time.items() if (last_time - current_time) > 35]
            for ip in inactive:
                self._delete_ips_from_inactive_routes(ip)
                del self._receive_time[ip]
            time.sleep(5)
                
    def _delete_ips_from_inactive_routes(self, remove_ip):
        idx = [idx for idx, _ in enumerate(self._router_table['ip_destino']) if self._router_table['ip_saida'][idx] == remove_ip]
        for i in idx:
            del self._router_table['ip_destino'][i]
            del self._router_table['metrica'][i]
            del self._router_table['ip_saida'][i]
            
    def send_router_table(self):
        ip = 1 #TODO: Criar função que pega o ip que tem q enviar (nao precisa ser criada nessa classe)
        port = 9000 #TODO: Mesma coisa que acima 
        message = ''.join([f'@{router['ip_destino']}-{router['metrica']}' for router in self._router_table])
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.sendto(message.encode(),(ip,port))
        sock.close()
    
    def receive_router_table(self):
        """Recebe mensagens de roteadores vizinhos e atualiza a tabela de roteamento."""
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.bind((self._ip, self._port))
        while True:
            data, addr = sock.recvfrom(1024)
            if not data:
                continue
            self._receive_time[addr[0]] = time.time()
            data = data.decode() 
            routers = data.split('@')
            for rout in routers:
                info = rout.split('-')
                if info[0] not in self._router_table['ip_destino']:
                    metric = int(info[1]) + 1
                    self._add_rout(info[0],metric,addr[0])
                    self.send_router_table()