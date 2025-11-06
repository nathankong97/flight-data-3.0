# Feature Request: Spike Analysis - long term archive strategy                                                                                                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                     
  ## Context                                                                                                                                                                                                                                                                                                                                                        
  - currently, after 10 days scraping, we have 469,509 rows in total in `flights` table, 200M                                                                                                                                                                                                                                                                                                                                  
  - My server specification, and this is not the only: 
  - ```text
    System:    Kernel: 5.10.0-27-amd64 x86_64 bits: 64 compiler: gcc v: 10.2.1 Console: tty 3
           Distro: Debian GNU/Linux 11 (bullseye)
    Machine:   Type: Kvm Mobo: DigitalOcean model: Droplet v: 20171212 serial: <filter> BIOS: DigitalOcean v: 20171212
               date: 12/12/2017
    CPU:       Info: Dual Core model: DO-Regular bits: 64 type: MCP arch: Haswell rev: 2 L2 cache: 4 MiB
               flags: avx avx2 lm nx pae sse sse2 sse3 sse4_1 sse4_2 ssse3 vmx bogomips: 9178
               Speed: 2295 MHz min/max: N/A Core speeds (MHz): 1: 2295 2: 2295
    Graphics:  Device-1: Red Hat Virtio GPU driver: virtio-pci v: 1 bus ID: 00:02.0
               Display: server: No display server data found. Headless machine? tty: 120x32
               Message: Advanced graphics data unavailable in console for root.
    Audio:     Message: No Device data found.
    Network:   Device-1: Intel 82371AB/EB/MB PIIX4 ACPI vendor: Red Hat Qemu virtual machine type: network bridge
               driver: piix4_smbus v: N/A port: c180 bus ID: 00:01.3
               Device-2: Red Hat Virtio network driver: virtio-pci v: 1 port: c1a0 bus ID: 00:03.0
               IF: eth0 state: up speed: -1 duplex: unknown mac: <filter>
               Device-3: Red Hat Virtio network driver: virtio-pci v: 1 port: c1c0 bus ID: 00:04.0
               IF: eth1 state: up speed: -1 duplex: unknown mac: <filter>
               IF-ID-1: br-79885740c794 state: up speed: 10000 Mbps duplex: unknown mac: <filter>
               IF-ID-2: docker0 state: up speed: 10000 Mbps duplex: unknown mac: <filter>
               IF-ID-3: tailscale0 state: unknown speed: -1 duplex: full mac: N/A
               IF-ID-4: veth0214c4c state: up speed: 10000 Mbps duplex: full mac: <filter>
               IF-ID-5: veth851c133 state: up speed: 10000 Mbps duplex: full mac: <filter>
    Drives:    Local Storage: total: 80 GiB used: 130.42 GiB (163.0%)
               ID-1: /dev/vda model: N/A size: 80 GiB
               ID-2: /dev/vdb model: N/A size: 474 KiB
    Partition: ID-1: / size: 78.58 GiB used: 65.2 GiB (83.0%) fs: ext4 dev: /dev/vda1
               ID-2: /boot/efi size: 123.7 MiB used: 10.7 MiB (8.6%) fs: vfat dev: /dev/vda15
    Swap:      Alert: No Swap data was found.
    Sensors:   Message: No sensors data was found. Is sensors configured?
    Info:      Processes: 158 Uptime: 659d 5h 48m Memory: 3.83 GiB used: 1.7 GiB (44.3%) Init: systemd runlevel: 5
               Compilers: gcc: 10.2.1 Packages: 1258 Shell: Bash v: 5.1.4 inxi: 3.3.01
    ```
  - What is the best way to save old data
  - Define old data: 30 days, 60 days, 90 days, or more?
  - What is the ideal format to store in long term?
  - Free options
                                                                                                                                                                                                                                                                                                                                                                     
  ## Desired Outcome                                                                                                                                                                                                                                                                                                                                                 
  - Best approach to conclude this analysis
  - Give me the final solution

  ## Result
  - Keep the last 30 days in Postgres; everything older moves out.                                                                                                                                                                                                                                                                                                   
  - Partition flights monthly on sched_dep/created_at.                                                                                                                                                                                                                                                                                                               
  - On the first of each month: export the previous month’s partition to Parquet (Snappy), upload to cheap storage, verify, then drop that partition.                                                                                                                                                                                                                
  - Keep a simple manifest (row counts + checksum) and monitor the job/disk usage.                                                                                                                                                                                                                                                                                   
  - Optional: build small route/airline summaries to keep in Postgres longer; use DuckDB/Athena later if you need to query the archives.