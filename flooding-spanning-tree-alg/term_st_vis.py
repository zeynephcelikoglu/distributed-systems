"""
Term_ST: Sonlanma Tespiti (Termination Detection) İçeren Flooding Tabanlı
Asenkron Yayılan Ağaç (Spanning Tree) Algoritması

Algoritmanın özeti
------------------
1. Root, tüm komşularına <probe> mesajı göndererek ağacı oluşturmaya başlar.
2. IDLE durumundaki bir node ilk <probe> mesajını aldığında göndereni parent olarak seçer ve <probe> mesajını diğer komşularına iletir.
3. Zaten parentı olan node, sonradan gelen <probe> mesajlarına <reject> döner.
4. Bir node, parentı dışındaki tüm komşularından yanıt aldığında alt ağacının tamamlandığını anlar ve parentına <ack> gönderir (convergecast).
5. Aynı durumu root da sağladığında root, algoritmanın global olarak sonlandığını anlar.
"""
import random
import sys

sys.path.insert(1, '.')
from source import DawnSimVis, config

# Simülasyon parametreleri
ROOT = 0          # Ağacı başlatan nodeun kimliği
TX_RANGE = 120    # İletişim menzili (iki node arası mesafe bunu aşarsa komşu değiller)
SPACING = 100     # Grid noktaları arasındaki mesafe
JITTER = 25       # Grid konumlarına eklenen rastgele sapma

# Asenkron: her mesajın iletim gecikmesi rastgele seçilir
config.SIM_MESSAGGING_DELAY_TYPE = 'random'

# Node durumları (IDLE -> XPLORD -> TERM)
IDLE = 'IDLE'        # Hiç <probe> almadı
XPLORD = 'XPLORD'    # Keşif aşamasında (komşularından yanıt bekliyor)
TERM = 'TERM'        # Kendi alt ağacı bitti

# RGB
COLOR_IDLE = (.7, .7, .7)       # Gri     : IDLE
COLOR_ROOT = (1, 0, 0)          # Kırmızı : kök düğüm
COLOR_XPLORD = (1, .75, 0)      # Turuncu : XPLORD
COLOR_TERM = (0, .7, 0)         # Yeşil   : alt ağacı tamamlanmış node
COLOR_ROOT_DONE = (.6, 0, .8)   # Mor     : root global sonlanmayı anladı


class Node(DawnSimVis.BaseNode):

    def init(self):
        self.currstate = IDLE
        self.parent = None       # henüz parent yok
        self.childs = set()      # ack gönderen komşular
        self.others = set()      # reject gönderen komşular

        # Γ(i): iletişim menzili içindeki komşular
        self.nbrs = {n.id for d, n in self.neighbor_distance_list if d <= self.tx_range}

    def run(self):
        """ROOT, ağaç oluşturmayı başlatır."""
        if self.id == ROOT:
            self.change_color(*COLOR_ROOT)
            self.log(f'ROOT: probe gönderiliyor -> {sorted(self.nbrs)}')
            self.send_to_all(self.nbrs, 'probe')
            self.currstate = XPLORD
            # Rootun komşusu yoksa hemen sonlanır
            self.check_termination()
        else:
            self.change_color(*COLOR_IDLE)

    def on_receive(self, pck):
        j = pck['src']       # mesajı gönderen komşu
        typ = pck['type']    # probe, ack, reject

        # Durum: IDLE 
        if self.currstate == IDLE:
            if typ == 'probe':
                # İlk probe gönderen parent olur, keşif aşamasına geçer
                self.parent = j
                self.currstate = XPLORD
                self.scene.addlink(j, self.id, 'prev')   # parent-child ilişkisi çiz (tree edge)
                self.change_color(*COLOR_XPLORD)
                self.log(f'probe({j}) ilk kez alındı -> parent={j}')

                # Parent dışındaki tüm komşulara ilet
                self.send_to_all(self.nbrs - {j}, 'probe')

                # Parent dışında komşu yoksa hemen ack gönder
                self.check_termination()
            return

        # Durum: XPLORD 
        if typ == 'probe':
            # Nodeun zaten parentı var, tree edge olamaz
            self.log(f'probe({j}) daha önce alındı -> reject')
            self.send_to(j, 'reject')
        elif typ == 'ack':
            # ack dönen node, alt ağacını tamamlamış bir child
            self.childs.add(j)
            self.log(f'ack({j}) alındı -> child')
        elif typ == 'reject':
            # reject dönen node, başka bir daldan ağaca katılmıştır (non-tree edge)
            self.others.add(j)
            self.log(f'reject({j}) alındı -> others')

        self.check_termination()

    def check_termination(self):
        """Sonlanmayı denetler. Parent dışındaki her komşudan <ack> ya da <reject> gelmeli."""
        if self.currstate != XPLORD:
            return

        beklenen = self.nbrs - {self.parent}
        if (self.childs | self.others) != beklenen:
            return    # yanıt bekleyen komşu var

        # Tüm komşulardan yanıt geldi, nodeun alt ağacı tamamlandı
        if self.id != ROOT:
            # Convergecast: alt ağacın bittiğini parenta bildir
            self.send_to(self.parent, 'ack')
            self.change_color(*COLOR_TERM)
            self.log(f'alt ağaç tamamlandı, ack({self.id}) -> parent {self.parent}')
        else:
            # Root tüm ağın sonlandığı anlar
            self.change_color(*COLOR_ROOT_DONE)
            self.log('*** ROOT: ALGORİTMA GLOBAL OLARAK SONLANDI (termination detected) ***')

        self.currstate = TERM

    def send_to(self, dest, typ):
        """Sadece bir komşusuna, mesaj türünü ve gönderenini yollar."""
        self.send(dest, {'type': typ, 'src': self.id})

    def send_to_all(self, dests, typ):
        """Komşuların hepsine mesaj yollar. sorted() gönderim sırasının her çalıştırmada aynı olmasını sağlar."""
        for d in sorted(dests):
            self.send_to(d, typ)


def create_network():
    rnd = random.Random(1)
    for x in range(6):     
        for y in range(6):
            px = 50 + x * SPACING + rnd.uniform(-JITTER, JITTER)
            py = 50 + y * SPACING + rnd.uniform(-JITTER, JITTER)
            sim.add_node(Node, pos=(px, py), tx_range=TX_RANGE)

sim = DawnSimVis.Simulator(
    duration=100,
    timescale=1,
    visual=True,
    terrain_size=(650, 650),
    title='Term_ST - Sonlanma Tespitli Yayılan Ağaç')

# Ağı oluştur
create_network()

# Simülasyonu başlat
sim.run()