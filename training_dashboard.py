import os
import re
import time
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from datetime import datetime, timedelta

console = Console()

LOG_PATH = "train_qwen.log"
TOTAL_STEPS = 5000

def clear_screen():
    """Terminal ekranını tamamen temizle"""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_cpu_nvme():
    try:
        output = subprocess.check_output(["sensors"]).decode()
        cpu_match = re.search(r"Package id 0:\s+\+([\d\.]+)", output)
        nvme_match = re.search(r"Composite:\s+\+([\d\.]+)", output)
        cpu_temp = float(cpu_match.group(1)) if cpu_match else None
        nvme_temp = float(nvme_match.group(1)) if nvme_match else None
        return cpu_temp, nvme_temp
    except:
        return None, None

def get_gpu():
    try:
        output = subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=temperature.gpu,utilization.gpu,fan.speed,power.draw,memory.used,memory.total",
            "--format=csv,noheader,nounits"
        ]).decode().strip()
        t, util, fan, power, mem_used, mem_total = map(float, output.split(","))
        return t, util, fan, power, mem_used, mem_total
    except:
        return None, None, None, None, None, None

def parse_training_log():
    if not os.path.exists(LOG_PATH):
        return None, None, None, None, None
    
    try:
        with open(LOG_PATH, "r") as f:
            lines = f.readlines()
        
        current_step = None
        loss = None
        lr = None
        epoch = None
        step_time = None
        
        for line in reversed(lines):
            step_match = re.search(r"(\d+)/5000", line)
            if step_match and current_step is None:
                current_step = int(step_match.group(1))
            
            loss_match = re.search(r"'loss':\s*([\d\.]+)", line)
            if loss_match and loss is None:
                loss = float(loss_match.group(1))
            
            lr_match = re.search(r"'learning_rate':\s*([\d\.e\-]+)", line)
            if lr_match and lr is None:
                lr = float(lr_match.group(1))
            
            epoch_match = re.search(r"'epoch':\s*([\d\.]+)", line)
            if epoch_match and epoch is None:
                epoch = float(epoch_match.group(1))
            
            time_match = re.search(r"([\d\.]+)s/it", line)
            if time_match and step_time is None:
                step_time = float(time_match.group(1))
            
            if all(x is not None for x in [current_step, loss, lr, epoch, step_time]):
                break
        
        return current_step, loss, lr, epoch, step_time
    except:
        return None, None, None, None, None

def colorize_temp(temp, low, high):
    if temp is None:
        return "[grey]-[/]"
    if temp < low:
        return f"[green bold]{temp:.1f}°C[/]"
    elif temp < high:
        return f"[yellow bold]{temp:.1f}°C[/]"
    else:
        return f"[red bold]{temp:.1f}°C[/]"

def main():
    start_time = time.time()
    
    while True:
        # Ekranı temizle
        print("\033[2J\033[H", end="")  # ANSI escape code - daha güvenilir
        
        # Veri toplama
        cpu, nvme = get_cpu_nvme()
        gpu_t, gpu_util, gpu_fan, gpu_power, gpu_mem_used, gpu_mem_total = get_gpu()
        current_step, loss, lr, epoch, step_time = parse_training_log()
        
        # Başlık
        console.print("\n" + "=" * 80, style="bold cyan")
        console.print(" " * 25 + "🚀 QWEN 2.5 TRAINING MONITOR 🚀", style="bold magenta")
        console.print("=" * 80 + "\n", style="bold cyan")
        
        # Layout oluştur
        layout = Layout()
        layout.split_row(
            Layout(name="left", ratio=1),
            Layout(name="middle", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        # SOL PANEL - Hardware
        hw_table = Table(title="⚙️  Hardware Status", title_style="bold cyan", box=None, padding=(0, 2))
        hw_table.add_column("Metric", style="cyan", width=15)
        hw_table.add_column("Value", justify="right", width=20)
        
        hw_table.add_row("CPU Temp", colorize_temp(cpu, 70, 85))
        hw_table.add_row("NVMe Temp", colorize_temp(nvme, 65, 80))
        hw_table.add_row("", "")
        
        if gpu_t is not None:
            hw_table.add_row("GPU Temp", colorize_temp(gpu_t, 80, 90))
            hw_table.add_row("GPU Util", f"[green bold]{gpu_util:.0f}%[/]")
            hw_table.add_row("GPU Fan", f"[cyan bold]{gpu_fan:.0f}%[/]")
            hw_table.add_row("GPU Power", f"[yellow bold]{gpu_power:.0f} W[/]")
            
            vram_pct = (gpu_mem_used / gpu_mem_total * 100) if gpu_mem_total else 0
            vram_color = "green" if vram_pct < 80 else "yellow" if vram_pct < 90 else "red"
            hw_table.add_row("GPU VRAM", f"[{vram_color} bold]{gpu_mem_used:.0f}/{gpu_mem_total:.0f} MB[/]")
            hw_table.add_row("VRAM Usage", f"[{vram_color} bold]{vram_pct:.1f}%[/]")
        
        layout["left"].update(Panel(hw_table, border_style="cyan"))
        
        # ORTA PANEL - Training
        train_table = Table(title="📊 Training Progress", title_style="bold green", box=None, padding=(0, 2))
        train_table.add_column("Metric", style="green", width=15)
        train_table.add_column("Value", justify="right", width=20)
        
        if current_step is not None:
            progress_pct = (current_step / TOTAL_STEPS * 100)
            train_table.add_row("Current Step", f"[bold]{current_step:,} / {TOTAL_STEPS:,}[/]")
            train_table.add_row("Progress", f"[green bold]{progress_pct:.2f}%[/]")
            train_table.add_row("", "")
            
            if loss is not None:
                loss_color = "green" if loss < 1.5 else "yellow" if loss < 2.0 else "red"
                train_table.add_row("Loss", f"[{loss_color} bold]{loss:.4f}[/]")
            
            if lr is not None:
                train_table.add_row("Learning Rate", f"[cyan]{lr:.2e}[/]")
            
            if epoch is not None:
                train_table.add_row("Epoch", f"[cyan]{epoch:.2f}[/]")
            
            train_table.add_row("", "")
            
            if step_time is not None:
                train_table.add_row("Step Time", f"[yellow bold]{step_time:.2f}s[/]")
                
                remaining_steps = TOTAL_STEPS - current_step
                remaining_seconds = remaining_steps * step_time
                remaining_time = timedelta(seconds=int(remaining_seconds))
                
                total_seconds = (current_step * step_time) + remaining_seconds
                total_time = timedelta(seconds=int(total_seconds))
                
                eta = datetime.now() + timedelta(seconds=remaining_seconds)
                
                train_table.add_row("Remaining", f"[magenta bold]{str(remaining_time)}[/]")
                train_table.add_row("Total Time", f"[cyan]{str(total_time)}[/]")
                train_table.add_row("ETA", f"[yellow bold]{eta.strftime('%d %b %H:%M')}[/]")
        else:
            train_table.add_row("Status", "[yellow]Waiting for training...[/]")
        
        layout["middle"].update(Panel(train_table, border_style="green"))
        
        # SAĞ PANEL - Checkpoints
        info_table = Table(title="💾 Checkpoints", title_style="bold magenta", box=None, padding=(0, 2))
        info_table.add_column("Step", style="magenta", width=10)
        info_table.add_column("Status", justify="left", width=25)
        
        checkpoints = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]
        
        for cp in checkpoints:
            if current_step is not None:
                if current_step >= cp:
                    info_table.add_row(f"{cp}", "[green]✓ Saved[/]")
                elif current_step >= cp - 50:
                    info_table.add_row(f"{cp}", "[yellow]⏳ Soon...[/]")
                else:
                    info_table.add_row(f"{cp}", "[grey]Pending[/]")
            else:
                info_table.add_row(f"{cp}", "[grey]Pending[/]")
        
        layout["right"].update(Panel(info_table, border_style="magenta"))
        
        # Layout göster
        console.print(layout)
        
        # Alt bilgi
        console.print(f"\n[dim]Last Update: {datetime.now().strftime('%H:%M:%S')} | " 
                     f"Refresh: 10s | Press Ctrl+C to exit[/]", justify="center")
        
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Monitoring stopped.[/]", justify="center")