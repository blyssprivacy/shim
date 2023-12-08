#
#  Copyright (c) 2023  NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# AMD_SEV_DIR=/home/blyss/hopper-enclave/AMDSEV/snp-release-2023-09-05
# VDD_IMAGE=/home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images/ubuntu22.04.qcow2
IMAGE_DIR=/home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images
AMD_SEV_DIR=/home/blyss/hopper-enclave/AMDSEV-latest
VDD_IMAGE=/home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images/ubuntu22.04.qcow2

#Hardware Settings
NVIDIA_GPU=41:00.0
MEM=64 #in GBs
FWDPORT=9899

doecho=false
docc=true

while getopts "exp:" flag
do
        case ${flag} in
                e) doecho=true;;
                x) docc=false;;
                p) FWDPORT=${OPTARG};;
        esac
done

NVIDIA_GPU=$(lspci -d 10de: | awk '/NVIDIA/{print $1}')
NVIDIA_PASSTHROUGH=$(lspci -n -s $NVIDIA_GPU | awk -F: '{print $4}' | awk '{print $1}')

if [ "$doecho" = true ]; then
         echo 10de $NVIDIA_PASSTHROUGH > /sys/bus/pci/drivers/vfio-pci/new_id
fi

if [ "$docc" = true ]; then
        USE_HCC=true
fi

# $AMD_SEV_DIR/usr/local/bin/qemu-system-x86_64 \
# ${USE_HCC:+ -machine confidential-guest-support=sev0,vmport=off} \
# ${USE_HCC:+ -object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1} \
# -enable-kvm -nographic -no-reboot \
# -cpu EPYC-v4 -machine q35 -smp 12,maxcpus=31 -m ${MEM}G,slots=2,maxmem=512G \
# -drive file=$VDD_IMAGE,if=none,id=disk0,format=qcow2 \
# -kernel $IMAGE_DIR/vmlinuz-copy \
# -initrd $IMAGE_DIR/initrd.img \
# -append "BOOT_IMAGE=/vmlinuz-6.2.0-33-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0" \
# -device virtio-scsi-pci,id=scsi0,disable-legacy=on,iommu_platform=true \
# -device scsi-hd,drive=disk0 \
# -device virtio-net-pci,disable-legacy=on,iommu_platform=true,netdev=vmnic,romfile= \
# -netdev user,id=vmnic,hostfwd=tcp::$FWDPORT-:22 \
# -device pcie-root-port,id=pci.1,bus=pcie.0 \
# -device vfio-pci,host=$NVIDIA_GPU,bus=pci.1


# $AMD_SEV_DIR/usr/local/bin/qemu-system-x86_64 \
# ${USE_HCC:+ -machine confidential-guest-support=sev0,vmport=off} \
# ${USE_HCC:+ -object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1} \
# -enable-kvm -nographic -no-reboot \
# -cpu EPYC-v4 -machine q35 -smp 12,maxcpus=31 -m ${MEM}G,slots=2,maxmem=512G \
# -drive if=pflash,format=raw,unit=0,file=$AMD_SEV_DIR/usr/local/share/qemu/OVMF_CODE.fd,readonly=on \
# -drive file=$VDD_IMAGE,if=none,id=disk0,format=qcow2 \
# -device virtio-scsi-pci,id=scsi0,disable-legacy=on,iommu_platform=true \
# -device scsi-hd,drive=disk0 \
# -device virtio-net-pci,disable-legacy=on,iommu_platform=true,netdev=vmnic,romfile= \
# -netdev user,id=vmnic,hostfwd=tcp::$FWDPORT-:22 \
# -device pcie-root-port,id=pci.1,bus=pcie.0 \
# -device vfio-pci,host=$NVIDIA_GPU,bus=pci.1 \
# -fw_cfg name=opt/ovmf/X-PciMmio64Mb,string=262144

# ${USE_HCC:+ -machine confidential-guest-support=sev0,vmport=off} \

# ${USE_HCC:+ -machine memory-backend=ram1,kvm-type=protected} \
# ${USE_HCC:+ -object memory-backend-memfd-private,id=ram1,size=${MEM}G,share=true} \
# ${USE_HCC:+ -machine memory-encryption=sev0,vmport=off} \

# ${USE_HCC:+ -machine confidential-guest-support=sev0,vmport=off} \
# ${USE_HCC:+ -object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1} \
# -machine memory-backend=ram1,kvm-type=protected  \

$AMD_SEV_DIR/usr/local/bin/qemu-system-x86_64 \
-machine memory-encryption=sev0,vmport=off  \
-object memory-backend-memfd-private,id=ram1,size=64G,share=true  \
-object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1,discard=none  \
-enable-kvm -nographic -no-reboot \
-cpu EPYC-v4 -machine q35 -smp 12,maxcpus=31 -m ${MEM}G,slots=2,maxmem=512G \
-drive if=pflash,format=raw,unit=0,file=$AMD_SEV_DIR/usr/local/share/qemu/OVMF.fd,readonly=on \
-drive file=$VDD_IMAGE,if=none,id=disk0,format=qcow2 \
-device virtio-scsi-pci,id=scsi0,disable-legacy=on,iommu_platform=true \
-device scsi-hd,drive=disk0 \
-device virtio-net-pci,disable-legacy=on,iommu_platform=true,netdev=vmnic,romfile= \
-netdev user,id=vmnic,hostfwd=tcp::$FWDPORT-:22 \
-device pcie-root-port,id=pci.1,bus=pcie.0 \
-device vfio-pci,host=$NVIDIA_GPU,bus=pci.1 \
-fw_cfg name=opt/ovmf/X-PciMmio64Mb,string=262144




# -append "dm-mod.create=\"dm-verity,,4,ro,0 1638400 verity 1 8:1 8:2 4096 4096 204800 1 sha256 fb1a5a0f00deb908d8b53cb270858975e76cf64105d412ce764225d53b8f3cfd 51934789604d1b92399c52e7cb149d1b3a1b74bbbcb103b2a0aaacbed5c08584 1 ignore_corruption \""
