import os
import json
import subprocess
import threading
import socket
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# Fitxer de configuració a la carpeta de l'usuari
DIRECTORI_USUARI = os.path.expanduser("~")
FITXER_CONFIG = os.path.join(DIRECTORI_USUARI, "dispositius_desats.json")

class RedControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control de Xarxa Local - Gestió de Dispositius")
        self.root.geometry("880x680")

        self.subxarxa_var = tk.StringVar(value="192.168.1")
        self.manual_ip_var = tk.StringVar()
        self.manual_alias_var = tk.StringVar()
        
        self.dispositius = {} 
        self.check_vars = {}

        self.crear_interficie()
        self.carregar_dispositius_desats()

    def crear_interficie(self):
        # --- Panell Superior: Escaneig i Afegir Manual ---
        frame_superior = ttk.Frame(self.root)
        frame_superior.pack(fill="x", padx=10, pady=5)

        # 1. Panell d'Escaneig
        frame_escaneig = ttk.LabelFrame(frame_superior, text=" 1. Escaneig de Xarxa ")
        frame_escaneig.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ttk.Label(frame_escaneig, text="Subxarxa:").pack(side="left", padx=5, pady=5)
        ttk.Entry(frame_escaneig, textvariable=self.subxarxa_var, width=11).pack(side="left", padx=2)

        self.btn_escanejar = ttk.Button(frame_escaneig, text="🔍 Escanejar", command=self.iniciar_escaneig)
        self.btn_escanejar.pack(side="left", padx=5)

        self.lbl_estat = ttk.Label(frame_escaneig, text="A punt")
        self.lbl_estat.pack(side="left", padx=5)

        # 2. Panell d'Afegir Dispositiu Manualment
        frame_manual = ttk.LabelFrame(frame_superior, text=" Afegir IP Manualment ")
        frame_manual.pack(side="right", fill="both", expand=False, padx=(5, 0))

        ttk.Label(frame_manual, text="IP:").pack(side="left", padx=(5, 2), pady=5)
        ttk.Entry(frame_manual, textvariable=self.manual_ip_var, width=14).pack(side="left", padx=2)

        ttk.Label(frame_manual, text="Àlies:").pack(side="left", padx=(5, 2))
        ttk.Entry(frame_manual, textvariable=self.manual_alias_var, width=15).pack(side="left", padx=2)

        ttk.Button(frame_manual, text="➕ Afegir", command=self.afegir_ip_manual).pack(side="left", padx=5)

        # --- Llista d'Ordinadors Desats/Detectats ---
        frame_llista = ttk.LabelFrame(self.root, text=" 2. Dispositius Registrats ")
        frame_llista.pack(fill="both", expand=True, padx=10, pady=5)

        # Controls superiors
        frame_controls_llista = ttk.Frame(frame_llista)
        frame_controls_llista.pack(fill="x", padx=5, pady=2)
        
        ttk.Button(frame_controls_llista, text="Marcar Tots", command=lambda: self.seleccionar_tots(True)).pack(side="left", padx=2)
        ttk.Button(frame_controls_llista, text="Desmarcar Tots", command=lambda: self.seleccionar_tots(False)).pack(side="left", padx=2)
        ttk.Button(frame_controls_llista, text="💾 Desar Canvis Ara", command=self.forca_desat_manual).pack(side="left", padx=10)
        ttk.Button(frame_controls_llista, text="🗑️ Esborrar Llista Desada", command=self.netejar_desats).pack(side="right", padx=2)

        # Capçalera de la taula
        frame_capcalera = ttk.Frame(frame_llista)
        frame_capcalera.pack(fill="x", padx=5, pady=(5, 2))
        
        ttk.Label(frame_capcalera, text="Sel.", width=4).pack(side="left", padx=2)
        ttk.Label(frame_capcalera, text="Nom Personalitzat (Àlies)", width=28, font=('TkDefaultFont', 9, 'bold')).pack(side="left", padx=5)
        ttk.Label(frame_capcalera, text="Adreça IP", width=16, font=('TkDefaultFont', 9, 'bold')).pack(side="left", padx=5)
        ttk.Label(frame_capcalera, text="Nom de Xarxa (Hostname)", font=('TkDefaultFont', 9, 'bold')).pack(side="left", padx=5)

        ttk.Separator(frame_llista, orient="horizontal").pack(fill="x", padx=5, pady=2)

        # Contenidor amb Scrollbar
        self.canvas = tk.Canvas(frame_llista)
        scrollbar = ttk.Scrollbar(frame_llista, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Panell d'Accions ---
        frame_accions = ttk.LabelFrame(self.root, text=" 3. Enviar Ordre ")
        frame_accions.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame_accions, text="⚡ Aturar", command=lambda: self.confirmar_accio("apagar")).pack(side="left", expand=True, padx=5, pady=5)
        ttk.Button(frame_accions, text="🔄 Reiniciar", command=lambda: self.confirmar_accio("reiniciar")).pack(side="left", expand=True, padx=5, pady=5)
        ttk.Button(frame_accions, text="🕒 Sincronitzar Hora", command=lambda: self.confirmar_accio("hora")).pack(side="left", expand=True, padx=5, pady=5)

    # --- Gestió Manual de IP ---
    def afegir_ip_manual(self):
        ip = self.manual_ip_var.get().strip()
        alias = self.manual_alias_var.get().strip()

        patro_ip = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
        if not re.match(patro_ip, ip):
            messagebox.showerror("Error d'IP", "S'il us plau, introdueix una adreça IP vàlida (ex: 192.168.1.50).")
            return

        if not alias:
            alias = f"Equip ({ip.split('.')[-1]})"

        hostname_detectat = self.obtenir_hostname(ip)

        self.dispositius[ip] = {
            "alias": alias,
            "hostname": hostname_detectat,
            "seleccionado": True
        }

        self.desar_dispositius()
        self.actualitzar_llista_ui()

        self.manual_ip_var.set("")
        self.manual_alias_var.set("")
        self.lbl_estat.config(text=f"IP {ip} afegida.")

    # --- Persistència JSON ---
    def desar_dispositius(self):
        try:
            with open(FITXER_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self.dispositius, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error en desar", f"No s'ha pogut desar el fitxer:\n{e}")
            return False

    def forca_desat_manual(self):
        if self.desar_dispositius():
            messagebox.showinfo("Desat", f"Dades i seleccions desades amb èxit a:\n{FITXER_CONFIG}")

    def carregar_dispositius_desats(self):
        if os.path.exists(FITXER_CONFIG):
            try:
                with open(FITXER_CONFIG, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    
                for ip, val in datos.items():
                    if isinstance(val, str):
                        self.dispositius[ip] = {"alias": val, "hostname": "Desconegut", "seleccionado": True}
                    else:
                        if "seleccionado" not in val:
                            val["seleccionado"] = True
                        self.dispositius[ip] = val
                        
                self.actualitzar_llista_ui()
                self.lbl_estat.config(text=f"S'han carregat {len(self.dispositius)} dispositius.")
            except Exception:
                self.dispositius = {}

    def netejar_desats(self):
        if messagebox.askyesno("Confirmar", "Vols esborrar la llista desada de dispositius?"):
            self.dispositius.clear()
            self.desar_dispositius()
            self.actualitzar_llista_ui()
            self.lbl_estat.config(text="Llista netejada.")

    # --- Escaneig de Xarxa ---
    def obtenir_hostname(self, ip):
        try:
            nombre, _, _ = socket.gethostbyaddr(ip)
            return nombre
        except Exception:
            return "No detectat"

    def ping_ip(self, ip):
        comando = ["ping", "-n", "1", "-w", "500", ip]
        resultado = subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if resultado.returncode == 0:
            hostname_detectat = self.obtenir_hostname(ip)
            if ip not in self.dispositius:
                self.dispositius[ip] = {
                    "alias": f"Equip ({ip.split('.')[-1]})",
                    "hostname": hostname_detectat,
                    "seleccionado": True
                }
            else:
                self.dispositius[ip]["hostname"] = hostname_detectat

    def iniciar_escaneig(self):
        self.btn_escanejar.config(state="disabled")
        self.lbl_estat.config(text="Escanejant xarxa...")
        threading.Thread(target=self.escanear_red, daemon=True).start()

    def escanear_red(self):
        subxarxa = self.subxarxa_var.get().strip()
        hilos = []

        for i in range(1, 255):
            ip = f"{subxarxa}.{i}"
            hilo = threading.Thread(target=self.ping_ip, args=(ip,))
            hilos.append(hilo)
            hilo.start()

        for hilo in hilos:
            hilo.join()

        self.desar_dispositius()
        self.root.after(0, self.actualitzar_llista_ui)

    # --- Renderitzat ---
    def actualitzar_llista_ui(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        ips_ordenades = sorted(self.dispositius.keys(), key=lambda x: [int(i) for i in x.split('.')])

        if not ips_ordenades:
            ttk.Label(self.scroll_frame, text="No hi ha dispositius registrats. Realitza un escaneig o afegeix una IP manualment.").pack(padx=10, pady=10)
        else:
            for ip in ips_ordenades:
                frame_item = ttk.Frame(self.scroll_frame)
                frame_item.pack(fill="x", anchor="w", padx=5, pady=3)

                # Casella de Selecció
                estat_previ = self.dispositius[ip].get("seleccionado", True)
                var = tk.BooleanVar(value=estat_previ)
                chk = ttk.Checkbutton(frame_item, variable=var, command=lambda target_ip=ip, b_var=var: self.desar_estat_seleccio(target_ip, b_var.get()))
                chk.pack(side="left", padx=(5, 10))

                # Nom Personalitzat (Àlies)
                alias_var = tk.StringVar(value=self.dispositius[ip].get("alias", ""))
                entry_alias = ttk.Entry(frame_item, textvariable=alias_var, width=28)
                entry_alias.pack(side="left", padx=5)

                entry_alias.bind("<FocusOut>", lambda event, target_ip=ip, a_var=alias_var: self.desar_alias(target_ip, a_var.get()))
                entry_alias.bind("<Return>", lambda event, target_ip=ip, a_var=alias_var: self.desar_alias(target_ip, a_var.get()))

                # Adreça IP
                lbl_ip = ttk.Label(frame_item, text=ip, width=16, font=('Courier', 10))
                lbl_ip.pack(side="left", padx=5)

                # Hostname
                hostname = self.dispositius[ip].get("hostname", "No detectat")
                lbl_hostname = ttk.Label(frame_item, text=hostname, foreground="#555555")
                lbl_hostname.pack(side="left", padx=5)

                self.check_vars[ip] = var

        self.btn_escanejar.config(state="normal")
        self.lbl_estat.config(text=f"Llista actualitzada. Total: {len(self.dispositius)} equips.")

    def desar_estat_seleccio(self, ip, estat):
        if ip in self.dispositius:
            self.dispositius[ip]["seleccionado"] = estat
            self.desar_dispositius()

    def desar_alias(self, ip, nou_alias):
        if ip in self.dispositius:
            self.dispositius[ip]["alias"] = nou_alias
            self.desar_dispositius()

    def seleccionar_tots(self, estat):
        for ip, var in self.check_vars.items():
            var.set(estat)
            if ip in self.dispositius:
                self.dispositius[ip]["seleccionado"] = estat
        self.desar_dispositius()

    # --- Enviament d'Ordres ---
    def obtenir_ips_seleccionades(self):
        return [ip for ip, var in self.check_vars.items() if var.get()]

    def confirmar_accio(self, accio):
        seleccionats = self.obtenir_ips_seleccionades()
        if not seleccionats:
            messagebox.showwarning("Atenció", "Has de seleccionar almenys un ordinador.")
            return

        noms_accions = {
            "apagar": "aturar",
            "reiniciar": "reiniciar",
            "hora": "sincronitzar hora"
        }

        if messagebox.askyesno("Confirmar", f"Vols executar '{noms_accions.get(accio, accio)}' en {len(seleccionats)} ordinador(s)?"):
            threading.Thread(target=self.executar_ordres, args=(accio, seleccionats), daemon=True).start()

# Les comandes que executen les ordres als sistemes clients
# Has de tenir 4 espais abans de 'def'
    def executar_ordres(self, accio, ips):
        data_cmd = datetime.now().strftime("%d-%m-%Y")
        hora_cmd = datetime.now().strftime("%H:%M:%S")

        for ip in ips:
            if accio == "apagar":
                cmd = f"shutdown /m \\\\{ip} /s /f /t 0"
            elif accio == "reiniciar":
                cmd = f"shutdown /m \\\\{ip} /r /f /t 0"
            elif accio == "hora":
                            # Atura el servei de temps, canvia la data/hora, actualitza el maquinari i ho torna a activar
                            comanda_interna = (
                                f"net stop w32time & "
                                f"date {data_cmd} & "
                                f"time {hora_cmd} & "
                                f"w32tm /resync /force & "
                                f"net start w32time"
                            )
                            cmd = f'wmic /node:"{ip}" process call create "cmd.exe /c {comanda_interna}"'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.root.after(0, lambda: messagebox.showinfo("Èxit", f"L'ordre de '{accio}' s'ha enviat correctament als equips."))

if __name__ == "__main__":
    root = tk.Tk()
    app = RedControlApp(root)
    root.mainloop()