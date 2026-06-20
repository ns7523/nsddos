#!/usr/bin/env python3

from __future__ import annotations

import signal
import sys
import time

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import SingleSwitchTopo


def main() -> int:
    controller_host = sys.argv[1]
    controller_port = int(sys.argv[2])
    fanout = int(sys.argv[3])

    topo = SingleSwitchTopo(k=fanout)
    net = Mininet(topo=topo, controller=None, switch=OVSSwitch, autoSetMacs=True)
    net.addController("c0", controller=RemoteController, ip=controller_host, port=controller_port)
    net.start()

    def shutdown(*_args) -> None:
        net.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
