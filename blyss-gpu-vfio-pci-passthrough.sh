#!/bin/bash

modprobe vfio-pci
sh -c "echo 10de 2331 > /sys/bus/pci/drivers/vfio-pci/new_id"
