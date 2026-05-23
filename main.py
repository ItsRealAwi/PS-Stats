import pyglet
from pyglet import shapes
from pyglet.window import key
import psutil
import time
import ctypes
import webbrowser
import socket
import platform
import os
import threading
import subprocess

HWND_TOPMOST = -1
SWP_NOSIZE = 1
SWP_NOMOVE = 2
WM_NCLBUTTONDOWN = 0xA1
HTCAPTION = 2

class UltimateKernelMonitor(pyglet.window.Window):
    def __init__(self):
        super().__init__(width=1500, height=850, style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS)
        ctypes.windll.user32.SetWindowPos(self._hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        pyglet.gl.glClearColor(0.02, 0.02, 0.02, 1.0) 

        self.running = True
        self.data_cols = ["DATA LOADING...", "DATA LOADING...", "DATA LOADING..."]
        self.is_collapsed = False
        
        font_name = 'Consolas'
        font_size = 9
        
        self.lbl_col1 = pyglet.text.Label("", font_name=font_name, font_size=font_size,
                                          x=20, y=self.height - 20, anchor_x='left', anchor_y='top',
                                          width=480, multiline=True, color=(0, 255, 150, 255))
                                          
        self.lbl_col2 = pyglet.text.Label("", font_name=font_name, font_size=font_size,
                                          x=520, y=self.height - 20, anchor_x='left', anchor_y='top',
                                          width=480, multiline=True, color=(0, 255, 150, 255))
                                          
        self.lbl_col3 = pyglet.text.Label("", font_name=font_name, font_size=font_size,
                                          x=1020, y=self.height - 20, anchor_x='left', anchor_y='top',
                                          width=460, multiline=True, color=(0, 255, 150, 255))

        self.btn_rect = shapes.Rectangle(x=20, y=15, width=1460, height=40, color=(15, 15, 15))
        self.btn_label = pyglet.text.Label(
            "[ INITIALIZE TRANSFER / DONATE ]", 
            font_name='Consolas', font_size=12,
            x=self.width // 2, y=35, anchor_x='center', anchor_y='center', 
            color=(255, 204, 0, 255)
        )

        self.boot_time = psutil.boot_time()
        self.thread = threading.Thread(target=self.hardware_polling, daemon=True)
        self.thread.start()

    def get_gpu_info(self):
        try:
            out = subprocess.getoutput("nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader")
            if "not recognized" in out or not out:
                return "GPU: Integrated / AMD / NVIDIA not found"
            parts = out.split(',')
            return (f"Name   : {parts[0].strip()}\n"
                    f"Load   : {parts[2].strip()} | Temp: {parts[1].strip()}°C\n"
                    f"VRAM   : {parts[3].strip()} / {parts[4].strip()}")
        except:
            return "GPU: Reading unavailable"

    def hardware_polling(self):
        last_net = psutil.net_io_counters()
        last_disk = psutil.disk_io_counters()
        last_time = time.time()

        while self.running:
            now = time.time()
            dt = now - last_time
            last_time = now
            
            cpu_pct = psutil.cpu_percent(percpu=True)
            cpu_freq = psutil.cpu_freq()
            cpu_stats = psutil.cpu_stats()
            
            cores_str = "\n".join([f"  CORE {i:02d}: [{'#'*int(p/5):<20}] {p:>5.1f}%" for i, p in enumerate(cpu_pct)])
            
            mem = psutil.virtual_memory()
            swp = psutil.swap_memory()
            uptime = int(now - self.boot_time)

            col1 = (
                f"=== [ SYSTEM CORE ] ===================================\n"
                f"OS      : {platform.system()} {platform.release()} ({platform.version()})\n"
                f"ARCH    : {platform.machine()} | NODE: {platform.node()}\n"
                f"UPTIME  : {uptime//3600:02d}h {(uptime%3600)//60:02d}m {uptime%60:02d}s\n"
                f"\n=== [ CPU KERNEL STATS ] ==============================\n"
                f"CTX SWITCHES: {cpu_stats.ctx_switches:,}\n"
                f"INTERRUPTS  : {cpu_stats.interrupts:,}\n"
                f"SYSCALLS    : {getattr(cpu_stats, 'syscalls', 'N/A')}\n"
                f"FREQ        : {cpu_freq.current:.1f} MHz (Max: {cpu_freq.max:.1f})\n"
                f"\n=== [ CPU LOAD ] ======================================\n"
                f"{cores_str}\n"
                f"\n=== [ MEMORY ALLOCATION ] =============================\n"
                f"RAM TOTAL   : {mem.total / (1024**3):.2f} GB\n"
                f"RAM USED    : {mem.used / (1024**3):.2f} GB ({mem.percent}%)\n"
                f"RAM FREE    : {mem.free / (1024**3):.2f} GB\n"
                f"RAM ACTIVE  : {getattr(mem, 'active', 0) / (1024**3):.2f} GB\n"
                f"RAM AVAIL   : {mem.available / (1024**3):.2f} GB\n"
                f"\n=== [ PAGING / SWAP ] =================================\n"
                f"SWAP TOTAL  : {swp.total / (1024**3):.2f} GB\n"
                f"SWAP USED   : {swp.used / (1024**3):.2f} GB ({swp.percent}%)\n"
                f"PAGE IN     : {swp.sin:,} bytes\n"
                f"PAGE OUT    : {swp.sout:,} bytes\n"
            )
            
            disk_io = psutil.disk_io_counters()
            r_spd = (disk_io.read_bytes - last_disk.read_bytes) / dt
            w_spd = (disk_io.write_bytes - last_disk.write_bytes) / dt
            last_disk = disk_io

            parts_str = ""
            for p in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    parts_str += (f"  [{p.device}]\n"
                                  f"  FS: {p.fstype:<6} | MNT: {p.mountpoint}\n"
                                  f"  TOTAL: {usage.total/(1024**3):>6.1f} GB\n"
                                  f"  USED : {usage.used/(1024**3):>6.1f} GB ({usage.percent}%)\n"
                                  f"  FREE : {usage.free/(1024**3):>6.1f} GB\n"
                                  f"  {'-'*40}\n")
                except: pass

            gpu_str = self.get_gpu_info()

            col2 = (
                f"=== [ HARDWARE & GPU ] ================================\n"
                f"{gpu_str}\n"
                f"\n=== [ DISK I/O METRICS ] ==============================\n"
                f"READ SPEED  : {r_spd/1024**2:.2f} MB/s\n"
                f"WRITE SPEED : {w_spd/1024**2:.2f} MB/s\n"
                f"READ COUNTS : {disk_io.read_count:,} ops\n"
                f"WRITE COUNTS: {disk_io.write_count:,} ops\n"
                f"READ TIME   : {disk_io.read_time} ms\n"
                f"WRITE TIME  : {disk_io.write_time} ms\n"
                f"\n=== [ MOUNTED FILESYSTEMS ] ===========================\n"
                f"{parts_str}"
            )
            
            net_io = psutil.net_io_counters()
            d_spd = (net_io.bytes_recv - last_net.bytes_recv) / dt
            u_spd = (net_io.bytes_sent - last_net.bytes_sent) / dt
            last_net = net_io

            conns = psutil.net_connections(kind='inet')
            c_states = {}
            for c in conns:
                c_states[c.status] = c_states.get(c.status, 0) + 1
            conn_str = "\n".join([f"  {k:<12}: {v}" for k, v in c_states.items()])
            
            procs = []
            for p in psutil.process_iter(['name', 'memory_percent']):
                try: procs.append(p.info)
                except: pass
            top_mem = sorted(procs, key=lambda x: x['memory_percent'] or 0, reverse=True)[:6]
            top_str = "\n".join([f"  {p['name'][:20]:<20} | {p['memory_percent']:.1f}%" for p in top_mem])

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            active_app = "Unknown"
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                active_app = buf.value[:40]

            col3 = (
                f"=== [ NETWORK INTERFACE ] =============================\n"
                f"IP ADDRESS  : {socket.gethostbyname(socket.gethostname())}\n"
                f"DOWNLOAD    : {d_spd/1024:.1f} KB/s\n"
                f"UPLOAD      : {u_spd/1024:.1f} KB/s\n"
                f"PACKETS IN  : {net_io.packets_recv:,}\n"
                f"PACKETS OUT : {net_io.packets_sent:,}\n"
                f"ERR IN/OUT  : {net_io.errin} / {net_io.errout}\n"
                f"DROP IN/OUT : {net_io.dropin} / {net_io.dropout}\n"
                f"\n=== [ TCP/UDP SOCKET STATES ] =========================\n"
                f"TOTAL CONNS : {len(conns)}\n"
                f"{conn_str}\n"
                f"\n=== [ PROCESS HEURISTICS ] ============================\n"
                f"TOTAL PROCS : {len(psutil.pids())}\n"
                f"ACTIVE WIN  : {active_app}\n"
                f"\n  [ TOP MEMORY CONSUMERS ]\n{top_str}\n"
            )

            self.data_cols = [col1, col2, col3]
            time.sleep(1)

    def on_draw(self):
        self.clear()
        self.lbl_col1.text = self.data_cols[0]
        self.lbl_col2.text = self.data_cols[1]
        self.lbl_col3.text = self.data_cols[2]
        self.lbl_col1.draw()
        self.lbl_col2.draw()
        self.lbl_col3.draw()
        self.btn_rect.draw()
        self.btn_label.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            if 15 <= x <= 1475 and 15 <= y <= 55:
                webbrowser.open("https://donatello.to/") 
            else:
                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.SendMessageW(self._hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)

    def on_key_press(self, symbol, modifiers):
        if symbol == key.ESCAPE:
            self.running = False
            self.close()

if __name__ == "__main__":
    app = UltimateKernelMonitor()
    pyglet.app.run()
