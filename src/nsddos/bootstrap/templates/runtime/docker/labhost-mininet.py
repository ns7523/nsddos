#!/usr/bin/env python3
"""Launch Mininet topology inside labhost container."""

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import SingleSwitchTopo


def main() -> None:
    topo = SingleSwitchTopo(k=3)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None)
    net.addController(RemoteController("c0", ip="floodlight", port=6653))
    net.start()
    net.interact()
    net.stop()


if __name__ == "__main__":
    main()
