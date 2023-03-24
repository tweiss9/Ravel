from ravel.app import RavelApp
from ravel.log import logger
from ravel.util import dpid_to_str


class LoadBalancer(RavelApp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vips = {}

    def get_next_server(self, vip):
        servers = self.vips[vip]['servers']
        index = self.vips[vip]['current_index']
        next_server = servers[index]
        self.vips[vip]['current_index'] = (index + 1) % len(servers)
        return next_server

    def _handle_arp(self, event):
        vip = event.parsed.payload.protodst
        if vip in self.vips:
            mac = self.vips[vip]['mac']
            actions = [event.ofproto_parser.OFPActionOutput(event.ofproto.OFPP_NORMAL)]
            self._install_flow(event, event.msg.match, actions)
            self.send_packet(event.msg.buffer_id, event.msg.in_port, mac, actions)

    def _handle_icmp(self, event):
        vip = event.parsed.payload.dst
        if vip in self.vips:
            server_ip = self.get_next_server(vip)
            server_mac = self.vips[vip]['servers'][server_ip]['mac']
            actions = [event.ofproto_parser.OFPActionSetField(eth_dst=server_mac),
                       event.ofproto_parser.OFPActionOutput(self.vips[vip]['servers'][server_ip]['port'])]
            self._install_flow(event, event.msg.match, actions)
            self.send_packet(event.msg.buffer_id, event.msg.in_port, server_mac, actions)

    def _install_flow(self, event, match, actions):
        dp = event.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        priority = 100
        idle_timeout = 10
        hard_timeout = 30
        buffer_id = event.ofproto.OFP_NO_BUFFER
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, buffer_id=buffer_id, priority=priority,
                                idle_timeout=idle_timeout, hard_timeout=hard_timeout,
                                match=match, instructions=inst)
        dp.send_msg(mod)

    def _update_config(self):
        with self.db.cursor() as cur:
            cur.execute('SELECT * FROM vips')
            rows = cur.fetchall()
            for row in rows:
                vip = row['vip']
                if vip not in self.vips:
                    self.vips[vip] = {}
                    self.vips[vip]['servers'] = {}
                    self.vips[vip]['current_index'] = 0
                self.vips[vip]['mac'] = row['mac']
                if row['server_ip'] not in self.vips[vip]['servers']:
                    self.vips[vip]['servers'][row['server_ip']] = {}
                self.vips[vip]['servers'][row['server_ip']]['mac'] = row['server_mac']
                self.vips[vip]['servers'][row['server_ip']]['port'] = row['server_port']

    def start(self):
        self._update_config()
        self.add_controller_packet_handler(self._handle_arp, ['arp'])
        self.add_controller_packet_handler(self._handle_icmp, ['icmp'])
        logger.info('LoadBalancer started')
