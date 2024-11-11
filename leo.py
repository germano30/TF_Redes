
import socket
import sys
import time
import random

class Router():
    def __init__(self):
        self.HOST = '172.20.10.2'
        self.PORT = 9000
        self.sock = None
        self.routing_table = {}
        self.NEIGHBORS = []
        self.updates_control = {}
        self.update_threshold = 10
        self.inactive_threshold = 30
    
    def instantiate_socket(self):
        # Cria o socket UDP
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.HOST, self.PORT))
            self.sock.settimeout(2)
            self.sock.setblocking(0)
            print("---> Socket criado com sucesso")
        except:
            print("Erro ao criar o socket, confira:")
            print("--> Endereço: ", self.HOST)
            print("--> Porta: ", self.PORT)
            exit(1)

    def start_routing_table(self):
        print("---> Inicializando tabela de roteamento")
        with open('config/neighbors.txt') as f:
            for neighbor in f:
                print(f"---> Registrando vizinho: {neighbor}", end='')
                neighbor = neighbor.strip().replace('\n', '')
                self.routing_table[neighbor] = {
                    'cost': 1,
                    'exit': neighbor
                }
                self.NEIGHBORS.append(neighbor)
        print('\n\n')
        self.fancy_print()

    def fancy_print(self):
        print("Tabela de roteamento:")
        print(f"{'Destino':^{15}} | {'Custo':^{5}} | {'Saída':^{15}}")
        print('-' * (40))
        for dest, reach in self.routing_table.items():
            print(f"{str(dest):^{15}} | {str(reach['cost']):^{5}} | {str(reach['exit']):^{15}}")
        print('\n\n')

    def update_routing_table(self, data, addr):
        if data.startswith('*'):
            return
        data = data.strip('@').split('@')
        for neighbor_reach in data:
            dest, reach = neighbor_reach.split('-')
            if dest == self.HOST:
                continue
            if dest not in self.routing_table.keys():
                self.routing_table[dest] = {
                            'cost': int(reach)+1,
                            'exit': addr
                        }
            if self.routing_table[dest]['cost'] > int(reach)+1:
                self.routing_table[dest] = {
                            'cost': int(reach)+1,
                            'exit': addr
                    }
    
    def verify_for_new_neighbor(self, data):
        if data.startswith('*'):
            new_neighbor = data.strip('*')
            if new_neighbor not in self.NEIGHBORS:
                print(f"---> Novo vizinho encontrado: {new_neighbor}")
                self.NEIGHBORS.append(new_neighbor)
                self.routing_table[new_neighbor] = {
                    'cost': 1,
                    'exit': new_neighbor
                }

    def send_update(self):
        prepare_routing_table = [f'{dst}-{reach['cost']}' for dst, reach in self.routing_table.items()]
        routing_table_str = '@'+'@'.join(prepare_routing_table)
        for neighbor_ip in self.NEIGHBORS:
            try:
                self.sock.sendto(routing_table_str.encode(), (neighbor_ip, self.PORT))
                print(f"---> Tabela de roteamento enviada para Roteador {neighbor_ip}: {routing_table_str}")
            except:
                print(f"---> Erro ao enviar mensagem para Roteador {neighbor_ip}")

        print('\n\n')


    def start_control_table(self):
        for neighbor in self.NEIGHBORS:
            self.updates_control[str(neighbor)] = time.time()

    def verify_neighbor_inactivity(self):
        inactives = set()
        for neighbor in self.NEIGHBORS:
            if time.time() - self.updates_control[str(neighbor)] > self.inactive_threshold:
                inactives.add(neighbor)
                del self.updates_control[neighbor]
                del self.NEIGHBORS[self.NEIGHBORS.index(neighbor)]
                print(f"---> Roteador {neighbor} está inativo.")
        
        dests_to_remove = set()
        for dest, reach in self.routing_table.items():
            if reach['exit'] in inactives:
                dests_to_remove.add(dest)

        for dest in dests_to_remove:
            del self.routing_table[dest]

    def listen(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            data = data.decode('utf-8')
            print(f"Recebido: {data} de {addr}")
            if data.startswith('@'):
                self.updates_control[addr[0]] = time.time()
                self.update_routing_table(data, addr[0])
            elif data.startswith('*'):
                self.verify_for_new_neighbor(data)
            elif data.startswith('!'):
                self.propagate_message(data)
        except socket.timeout:
            pass
        except BlockingIOError:
            pass

    def send_message(self):
        # select random destination
        if not self.routing_table.keys():
            return
        random_index = random.randint(0, len(self.routing_table.keys())-1)
        random_dest = list(self.routing_table.keys())[random_index]
        message = "Oi tudo bem?"
        try:
            self.sock.sendto(f"!{self.HOST};{random_dest};{message}".encode(), (self.routing_table[random_dest]['exit'], self.PORT))
            print(f"---> Mensagem enviada para {random_dest}: {message}")
        except:
            print(f"---> Erro ao enviar mensagem para {random_dest}")


    def propagate_message(self, data):
        # !192.168.1.2;192.168.1.1;Oi tudo bem?
        data = data.strip('!').split(';')
        orig = data[0]
        dest = data[1]
        message = data[2]
        if dest == self.HOST:
            print(f"---> Mensagem recebida de {orig}: {message}")
        else:
            if dest in self.routing_table.keys():
                next_hop = self.routing_table[dest]['exit']
                try:
                    self.sock.sendto(f"!{orig};{dest};{message}".encode(), (next_hop, self.PORT))
                    print(f"Repassando mensagem para {next_hop}: {message}")
                except:
                    print(f"Erro ao enviar mensagem para {next_hop}")
        print('\n\n')

    def run(self):
        self.instantiate_socket()

        self.start_routing_table()
        self.start_control_table()

        last_update_ts = time.time()
        last_message_ts = time.time()

        for neighbor in self.NEIGHBORS:
            print(f"Enviando mensagem de reconhecimento vizinho {neighbor}")
            self.sock.sendto(f"*{self.HOST}".encode(), (neighbor, self.PORT))
        while True:
            self.verify_neighbor_inactivity()

            if time.time() - last_update_ts > self.update_threshold:
                self.send_update()
                last_update_ts = time.time()
                self.fancy_print()

            self.listen()
            if time.time() - last_message_ts > 20:
                last_message_ts = time.time()
                self.send_message()
    

if __name__ == '__main__':
    router = Router()
    router.run()
