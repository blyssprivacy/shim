# Notes from installation

## Host
```sh
nvidia-settings # shows GPU temp

```

got `python: not found` when running `./build.sh --package`.

```sh
sudo apt install python2
sudo ln -s /usr/bin/python2 /usr/local/bin/python
```

```sh
cp nvtrust/infrastructure/linux/patches/*.patch AMDSEV
pushd /home/blyss/hopper-enclave/AMDSEV/linux/host

```

Set `GRUB_DISABLE_OS_PROBER=false` and:

```sh
sudo update-grub
```

In grub, go to Ubuntu "Advanced Boot Settings" and choose the patched 5.19 kernel

Make sure to press "e" when selecting "Ubuntu Server with the HWE Kernel"

```sh
sudo modprobe vfio-pci
sudo sh -c "echo 10de 2331 > /sys/bus/pci/drivers/vfio-pci/new_id"
```

## Guest
```sh
wget https://developer.download.nvidia.com/compute/cuda/12.2.2/local_installers/cuda_12.2.2_535.104.05_linux.run
sudo sh cuda_12.2.2_535.104.05_linux.run -m=kernel-open

sudo sh -c "echo 0000:41:00.0 > /sys/bus/pci/drivers/vfio-pci/unbind"
```


## Startup
```sh
sudo modprobe vfio-pci
sudo sh -c "echo 10de 2331 > /sys/bus/pci/drivers/vfio-pci/new_id"
# 2331 is from output of "lspci -d 10de:", should not change with GPU model
```

I have now moved these to a systemd service (blyss-gpu-vfio-pci).

## Extend disk
```
qemu-img create -f qcow2 -o preallocation=metadata images/large-ubuntu22.04.qcow2 800G
sudo virt-filesystems --long -h --all -a  images/ubuntu22.04.qcow2
sudo virt-resize --expand /dev/sda3 images/ubuntu22.04.
qcow2 images/large-ubuntu22.04.qcow2
sudo lvextend --extents +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
```

## Measuring boot

```
python3 ./sev-snp-measure.py --mode snp --vcpus=12 --vcpu-type=EPYC-v4 --ovmf=/home/blyss/hopper-enclave/AMDSEV/snp-release-2023-09-05/usr/local/share/qemu/OVMF_CODE.fd
```

## Enabling SME

```
in /etc/default/grub:
  GRUB_CMDLINE_LINUX_DEFAULT="quiet splash mem_encrypt=on"
sudo update-grub
```

```
sudo python3 ./sev-snp-measure.py --mode snp --vcpus=12 --vcpu-type=EPYC-v4 --ovmf=/home/blyss/hopper-enclave/AMDSEV-latest/usr/local/share/qemu/OVMF.fd --kernel /home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images/vmlinuz-copy --initrd /home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images/initrd.img --append "BOOT_IMAGE=/vmlinuz-6.2.0-33-generic root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0"
```

## Launch directly from kernel, initrd, append

```
sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz -initrd $DATA_DIR/images/initrd.img -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0" -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -sev-snp -default-network


dm-verity,,4,ro,0 1638400 verity 1 8:1 8:2 4096 4096 204800 1 sha256 fb1a5a0f00deb908d8b53cb270858975e76cf64105d412ce764225d53b8f3cfd 51934789604d1b92399c52e7cb149d1b3a1b74bbbcb103b2a0aaacbed5c08584 1 ignore_corruption
```

```
sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz -initrd $DATA_DIR/images/initrd.img -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0 dm-mod.create=\\\"dm-verity,,4,ro,0 1638400 verity 1 8:1 8:2 4096 4096 204800 1 sha256 fb1a5a0f00deb908d8b53cb270858975e76cf64105d412ce764225d53b8f3cfd 51934789604d1b92399c52e7cb149d1b3a1b74bbbcb103b2a0aaacbed5c08584 1 ignore_corruption\\\"" 


cd /home/blyss/hopper-enclave/AMDSEV-latest/snp-release-2023-09-24
export DATA_DIR=/home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts

sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz -initrd $DATA_DIR/images/initrd.img -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0 dm-mod.create=\\\"dm-verity,,4,ro,0 1638400 verity 1 8:1 8:2 4096 4096 204800 1 sha256 fb1a5a0f00deb908d8b53cb270858975e76cf64105d412ce764225d53b8f3cfd 51934789604d1b92399c52e7cb149d1b3a1b74bbbcb103b2a0aaacbed5c08584 1 ignore_corruption\\\"" 

sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz -initrd $DATA_DIR/images/initrd.img -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0 overlayroot=disabled" -sev-snp


sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz -initrd $DATA_DIR/images/initrd.img -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0 modules_load=dm-verity dm-mod.create=\\\"dm-verity,,4,ro,0 62500000 verity 1 253:0 253:0 4096 4096 7812500 7812501 sha256 0000000000000000000000000000000000000000000000000000000000000000 018f40fde2f120ce504e7bfcac2abd19d98dbfac050113f9ea18ce1ad9ecfdf1 1 ignore_corruption\\\"" -sev-snp

sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0 overlayroot="disabled" modules_load=dm-verity dm-mod.create=\\\"dm-verity,,4,ro,0 62500000 verity 1 8:3 8:3 4096 4096 7812500 7812501 sha256 0000000000000000000000000000000000000000000000000000000000000000 018f40fde2f120ce504e7bfcac2abd19d98dbfac050113f9ea18ce1ad9ecfdf1 1 ignore_corruption\\\"" -sev-snp


sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/new-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/ubuntu--vg-ubuntu--lv ro console=ttyS0 overlayroot=disabled"


# important not to set default-network here on first boot
sudo ./launch-qemu.sh -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.qcow2 -cdrom $DATA_DIR/isos/ubuntu-22.04.2-live-server-amd64.iso


sudo ./launch-qemu.sh -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.qcow2 -default-network
 -cdrom $DATA_DIR/isos/ubuntu-22.04.2-live-server-amd64.iso



sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/mapper/dm-verity ro console=ttyS0 overlayroot=disabled modules_load=dm-verity dm-mod.create=\\\"dm-verity,,4,ro,0 62500000 verity 1 /dev/sda2 /dev/sdb 4096 4096 7812500 2048 sha256 0000000000000000000000000000000000000000000000000000000000000000 02b4ba99ca69b69d012edf351040bb7c92a41d388deaca2af332c2f65d3727b2 1 ignore_corruption\\\""

```

sudo lvmdiskscan

## dmverity + overlayroot

This is a veritysetup call and a matching kernel command-line argument that sets up the device

```
# hash_offset = 4096 * hash_start_block
veritysetup  --verbose --debug --format=1 --data-block-size=4096 --hash-block-size=4096 --data-blocks=7812500 --hash-offset=32000004096 --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sda2




# uses offset of 50GB (if disk gets larger than that.... bad things happen)
# num_sectors * 512 == num_data_blocks * 4096 
# hash_start_block = num_data_blocks + 1

dm-verity,,4,ro,0 62500000 verity 1 253:0 253:0 4096 4096 7812500 7812501 sha256 0000000000000000000000000000000000000000000000000000000000000000 018f40fde2f120ce504e7bfcac2abd19d98dbfac050113f9ea18ce1ad9ecfdf1 1 ignore_corruption

dm-mod.create=\\\"dm-verity,,4,ro,0 62500000 verity 1 253:0 253:0 4096 4096 7812500 7812501 sha256 0000000000000000000000000000000000000000000000000000000000000000 018f40fde2f120ce504e7bfcac2abd19d98dbfac050113f9ea18ce1ad9ecfdf1 1 ignore_corruption\\\"



0000000000000000000000000000000000000000000000000000000000000000
```


## from start
These are commands from scratch:

```
export DATA_DIR=/home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts

# create a qcow2 image
# nb: it doesn't actually eat all 500 GB on disk
qemu-img create -f qcow2 -o preallocation=metadata images/no-lvm-ubuntu22.04.qcow2 500G

# launch standard (non-AmdSevX64, OVMF_CODE + OVMF_VARS) VM with Ubuntu ISO
# important not to set default-network here on first boot, and to give it enough memory
sudo ./launch-qemu.sh -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.qcow2 -cdrom $DATA_DIR/isos/ubuntu-22.04.2-live-server-amd64.iso

# choose:
#    hit 'e' on `Boot ... HWE..`
#    add 'console=ttyS0 ---'
#    hit ctrl-x
#    choose default settings, enable OpenSSH
#    uncheck "set up as LVM"

# now, launch VM
sudo ./launch-qemu.sh -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.qcow2 -default-network

# (to shut down VM later, do: sudo killall qemu-system-x86_64)

# change kernel to 5.6-rc2
scp -P 8000 ./linux/guest/*.deb  guest@localhost:/home/guest/
sudo dpkg -i *.deb

# on guest, via:
# ssh -p 8000 guest@localhost
# copy and chown
sudo cp /boot/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec .
sudo chown guest vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec
chmod 777 vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec

# back on host:
# get kernel, initrd
scp -P 8000 guest@localhost:/boot/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec /home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images
scp -P 8000 guest@localhost:/home/guest/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec /home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images

# do a qemu direct boot with kernel + initrd
# we need to use the AmdSevX64 version of launch-qemu now
# do:
sudo cp ../launch-qemu-AmdSevX64.sh ./launch-qemu.sh
sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/sda2 ro console=ttyS0 overlayroot=disabled"

# on guest:
# verify loaded kernel
uname -a
# should get: Linux hotbox-guest 6.5.0-rc2-snp-guest-ad9c0bf475ec

# still on guest:
# now, do dm-verity
# make the kernel module for dm-verity load in initramfs
# add it to /etc/initramfs-tools/modules
sudo vim /etc/initramfs-tools/modules # add "dm_verity"
sudo update-initramfs -u

# on host:
scp -P 8000 guest@localhost:/boot/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec /home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts/images

# on guest:
sudo veritysetup  --verbose --debug --format=1 --data-block-size=4096 --hash-block-size=4096 --hash-offset=8388608 --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sdb

sudo veritysetup  --verbose --debug --format=1 --data-block-size=4096 --hash-block-size=4096 --hash-offset=8388608 --data-blocks 7812500 --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sdb

sudo veritysetup  --verbose --debug --format=1 --data-block-size=4096 --hash-block-size=4096 --ignore-zero-blocks --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sdb


# new launch command on host:
sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/sda2 ro console=ttyS0 overlayroot=disabled" 

sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/sda2 ro console=ttyS0 overlayroot=tmpfs" 



sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -sev-snp -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec ro console=ttyS0 overlayroot=disabled modules_load=dm-verity dm-mod.create=\\\"dmverity,,0,ro,0 62500000 verity 1 /dev/sda2 /dev/sdb 4096 4096 7812500 0 sha256 0000000000000000000000000000000000000000000000000000000000000000 bc0ba6682d183b5896a68665a6e272795b11c6113822cd19f0721e6349fb285c 1 ignore_corruption\\\" root=/dev/dm-0 rootfstype=ext4" 


sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec ro console=ttyS0 overlayroot=disabled modules_load=dm-verity dm-mod.create=\\\"dmverity,,0,ro,0 62500000 verity 1 /dev/sda2 /dev/sdb 4096 4096 7812500 0 sha256 0000000000000000000000000000000000000000000000000000000000000000 bc0ba6682d183b5896a68665a6e272795b11c6113822cd19f0721e6349fb285c 1 ignore_corruption\\\" root=/dev/dm-0 rootfstype=ext4" 



sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec ro console=ttyS0 overlayroot=disabled root=/fasfdsafasdf rootfstype=ext4 dm-mod.create=\\\"dm-linear,,0,rw,0 62500000 linear /dev/sda2 0\\\"" 




sudo ./launch-qemu.sh -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec -mem 16384 -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 -hdb $DATA_DIR/images/scratch.qcow2 -default-network -append "BOOT_IMAGE=/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec root=/dev/dm-0 ro console=ttyS0 overlayroot=disabled modules_load=dm-verity dm-mod.create=\\\"dm-linear,,0,rw,0 62500000 linear /dev/sda2 0\\\"" 

# sudo veritysetup  --verbose --debug --format=1 --data-block-size=4096 --hash-block-size=4096 --data-blocks=130796288 --hash-offset=0 --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sdb

# b4dd7f198a6562b6f9d6b47ea700e84a7a98fb64f3aa6e8e8ff212baaaeed59d
# db0dc6f3dbade397fabab9b07f384c76414df3b9ba97087c0824f4a1d4416895

sudo ./launch-qemu.sh \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs root=/dev/dm-0 dm-mod.create=\\\"dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 b4dd7f198a6562b6f9d6b47ea700e84a7a98fb64f3aa6e8e8ff212baaaeed59d 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption\\\"" 

sudo ./launch-qemu.sh \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2" 


# sudo modprobe vfio-pci
# sudo sh -c "echo 10de 2331 > /sys/bus/pci/drivers/vfio-pci/new_id"

# to unbind and rebind:
# sudo sh -c "echo 0000:41:00.0 > /sys/bus/pci/drivers/vfio-pci/unbind"
# sudo sh -c "echo 0000:41:00.0 > /sys/bus/pci/drivers/vfio-pci/bind"

# turn CC on/off:
#   sudo python3 gpu_cc_tool.py --gpu-name=H100 --set-cc-mode on --reset-after-cc-mode-switch
# status:
#   sudo python3 gpu_cc_tool.py --gpu-name=H100 --query-cc-settings

# set GPU ready state with:
# (cd ~/nvtrust-private/guest_tools/gpu_verifiers/local_gpu_verifier)
# sudo python3 -m verifier.cc_admin
#
# run model (llama.cpp)
# make -j8 LLAMA_CUBLAS=1 LLAMA_CUDA_DMMV_X=64 LLAMA_CUDA_MMV_Y=8 LLAMA_CUDA_FORCE_DMMV=true LLAMA_CUDA_F16=true
# ./server -m models/phind-codellama-34b-v2.Q6_K.gguf -ngl 99999

# from ~/hopper-enclave/AMDSEV-latest/snp-release-2023-09-24
sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2" 


sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=tmpfs root=/dev/sda2 blyss_disable_server blyss_use_test_cert systemd.mask=ssh.service" 

sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 65000 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -hdc /home/blyss/models-img/models.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2 blyss_disable_server blyss_use_test_cert"

sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 65000 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2 blyss_disable_server blyss_use_test_cert"

sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2 blyss_use_test_cert"

sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs root=/dev/dm-0 dm-mod.create=\\\"dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 b4dd7f198a6562b6f9d6b47ea700e84a7a98fb64f3aa6e8e8ff212baaaeed59d 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption\\\"" 

sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 60000 \
  -enable-discard \
  -smp 4 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2 blyss_disable_server blyss_use_test_cert"

/usr/bin/time -v md5sum ~/llama.cpp/models/phind-codellama-34b-v2.Q6_K.gguf


sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=tmpfs root=/dev/sda2 blyss_use_test_cert"



# b4dd7f198a6562b6f9d6b47ea700e84a7a98fb64f3aa6e8e8ff212baaaeed59d



# sudo veritysetup --verbose --format=1 --data-block-size=4096 --hash-block-size=4096 --data-blocks=130796288 --hash-offset=0 --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sdb


sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -readonly \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs root=/dev/sda2 blyss_disable_server blyss_use_test_cert"

######## GOLDEN
sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -readonly \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs blyss_use_test_cert root=/dev/dm-0 rootflags=noload dm-mod.create=\\\"dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 db0dc6f3dbade397fabab9b07f384c76414df3b9ba97087c0824f4a1d4416895 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption\\\"" 




# measuring boot

python3 ./sev-snp-measure.py \
  --mode snp \
  --vcpus=8 \
  --vcpu-type=EPYC-v4 \
  --ovmf=/home/blyss/hopper-enclave/AMDSEV-latest/snp-release-2023-09-24/usr/local/share/qemu/OVMF.fd \
  --kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  --initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  --append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs blyss_use_test_cert root=/dev/dm-0 rootflags=noload dm-mod.create=\\\"dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 db0dc6f3dbade397fabab9b07f384c76414df3b9ba97087c0824f4a1d4416895 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption\\\"" 

fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs blyss_use_test_cert root=/dev/dm-0 dm-mod.create="dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 b4dd7f198a6562b6f9d6b47ea700e84a7a98fb64f3aa6e8e8ff212baaaeed59d 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption" initrd=initrd


  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2 blyss_disable_server blyss_use_test_cert systemd.unit=rescue.target"


sudo ./launch-qemu-AmdSevX64.sh -oldfw -mem 8192 -hda ../images/disk.qcow2 -cdrom ../iso/ubuntu-22.04.2-live-server-amd64.iso

sudo ./launch-qemu-AmdSevX64.sh \
  -mem 4096 \
  -smp 4 \
  -hda ../images/disk.qcow2 \
  -oldfw \
  -cdrom ../iso/ubuntu-22.04.2-live-server-amd64.iso \
  -kernel /mnt/casper/vmlinuz \
  -initrd /mnt/casper/initrd \
  -default-network \
  -append 'autoinstall ds=nocloud-net;s=http://_gateway:3003/'


sudo ./launch-qemu.sh \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs root=/dev/dm-0 dm-mod.create=\\\"dm-linear,,0,rw,0 1046370304 linear /dev/sda2 0\\\"" 
```

6a466da4-abe7-48b7-811a-b0e07a0ec982

7812500
130796288

## Final steps

```
# host boot:
sudo modprobe vfio-pci
sudo sh -c "echo 10de 2331 > /sys/bus/pci/drivers/vfio-pci/new_id"
cd ~/hopper-enclave/nvtrust/host_tools/python
sudo sh -c "echo 0000:41:00.0 > /sys/bus/pci/drivers/vfio-pci/unbind"
sudo python3 gpu_cc_tool.py --gpu-name=H100 --set-cc-mode on --reset-with-os --reset-after-cc-mode-switch
sudo sh -c "echo 0000:41:00.0 > /sys/bus/pci/drivers/vfio-pci/bind"

cd ~/hopper-enclave/AMDSEV-latest/snp-release-2023-09-24/
export DATA_DIR=/home/blyss/hopper-enclave/nvtrust/host_tools/sample_kvm_scripts

# Launching the VM to make modifications
sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "ro console=ttyS0 overlayroot=disabled root=/dev/sda2 blyss_disable_server blyss_use_test_cert"

# Launching the VM to calculate verity hash (~12 min)
sudo ./launch-qemu.sh \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -readonly \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs root=/dev/sda2 rootflags=noload blyss_disable_server blyss_use_test_cert"

time sudo veritysetup --verbose --format=1 --data-block-size=4096 --hash-block-size=4096 --data-blocks=130796288 --hash-offset=0 --salt=0000000000000000000000000000000000000000000000000000000000000000 format /dev/sda2 /dev/sdb

# sometimes:
# sudo /home/blyss/.cargo/bin/snphost reset

# Launching the VM in "clean" mode
sudo ./launch-qemu.sh \
  -gpu \
  -sev-snp \
  -kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  -mem 16384 \
  -smp 8 \
  -readonly \
  -hda $DATA_DIR/images/no-lvm-ubuntu22.04.qcow2 \
  -hdb $DATA_DIR/images/scratch.qcow2 \
  -default-network \
  -append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs root=/dev/dm-0 rootflags=noload dm-mod.create=\\\"dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 e1b26041c133bfe18e5aaffa6ad406a757c83308a9933e21d7f4bec986918b8b 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption\\\"" 

# Computing golden measurement
python3 ./sev-snp-measure.py \
  --mode snp \
  --vcpus=8 \
  --vcpu-type=EPYC-v4 \
  --ovmf=/home/blyss/hopper-enclave/AMDSEV-latest/snp-release-2023-09-24/usr/local/share/qemu/OVMF.fd \
  --kernel $DATA_DIR/images/vmlinuz-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  --initrd $DATA_DIR/images/initrd.img-6.5.0-rc2-snp-guest-ad9c0bf475ec \
  --append "fsck.mode=skip ro console=ttyS0 overlayroot=tmpfs blyss_use_test_cert root=/dev/dm-0 rootflags=noload dm-mod.create=\"dmverity,,0,ro,0 1046370304 verity 1 /dev/sda2 /dev/sdb 4096 4096 130796288 1 sha256 db0dc6f3dbade397fabab9b07f384c76414df3b9ba97087c0824f4a1d4416895 0000000000000000000000000000000000000000000000000000000000000000 1 panic_on_corruption\""

# produces measurement: 8650cab52f8537eb8c138f860d94beb7fc59141f0a8634b0b86633b2c7a3d99e122535f3137df5f064bd368eb92712ff
```