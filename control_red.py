import os
import json
import subprocess
import threading
import socket
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# Guardado en la carpeta del usuario para evitar problemas de permisos
DIRECTORIO_USUARIO = os.path.expanduser("~")
ARCHIVO_CONFIG = os.path.join(DIRECTORIO_USUARIO, "dispositivos_guardados.json")

class RedControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de dispositius de xarxa")
        self.root.geometry("850x600")

        self.subred_var = tk.StringVar(value="192.168.30")
        self.dispositivos = {} 
        self.check_vars = {}

        self.crear_interfaz()
        self.cargar_dispositivos_guardados()

    def crear_interfaz(self):
        # --- Panel de Escaneo ---
        frame_escaneo = ttk.LabelFrame(self.root, text=" 1. Escaneig de Red ")
        frame_escaneo.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_escaneo, text="Subred:").pack(side="left", padx=5, pady=5)
        ttk.Entry(frame_escaneo, textvariable=self.subred_var, width=12).pack(side="left", padx=5)

        self.btn_escanear = ttk.Button(frame_escaneo, text="🔍 Escaneajar Red", command=self.iniciar_escaneo)
        self.btn_escanear.pack(side="left", padx=5)

        self.lbl_estado = ttk.Label(frame_escaneo, text="Estado: Listo")
        self.lbl_estado.pack(side="left", padx=5)

        # --- Lista de Ordenadores Guardados/Detectados ---
        frame_lista = ttk.LabelFrame(self.root, text=" 2. Dispositius Registrats ")
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)

        # Controles superiores
        frame_controles_lista = ttk.Frame(frame_lista)
        frame_controles_lista.pack(fill="x", padx=5, pady=2)
        
        ttk.Button(frame_controles_lista, text="Marcar Tots", command=lambda: self.seleccionar_todos(True)).pack(side="left", padx=2)
        ttk.Button(frame_controles_lista, text="Desmarcar Tots", command=lambda: self.seleccionar_todos(False)).pack(side="left", padx=2)
        ttk.Button(frame_controles_lista, text="💾 Guardar Cambis Ara", command=self.fuerza_guardado_manual).pack(side="left", padx=10)
        ttk.Button(frame_controles_lista, text="🗑️ Borrar Llista Guardada", command=self.limpiar_guardados).pack(side="right", padx=2)

        # Cabecera de la tabla
        frame_cabecera = ttk.Frame(frame_lista)
        frame_cabecera.pack(fill="x", padx=5, pady=(5, 2))
        
        ttk.Label(frame_cabecera, text="Sel.", width=4).pack(side="left", padx=2)
        ttk.Label(frame_cabecera, text="Nombre Personalizado (Alias)", width=28, font=('TkDefaultFont', 9, 'bold')).pack(side="left", padx=5)
        ttk.Label(frame_cabecera, text="Dirección IP", width=16, font=('TkDefaultFont', 9, 'bold')).pack(side="left", padx=5)
        ttk.Label(frame_cabecera, text="Nombre de Red (Hostname)", font=('TkDefaultFont', 9, 'bold')).pack(side="left", padx=5)

        ttk.Separator(frame_lista, orient="horizontal").pack(fill="x", padx=5, pady=2)

        # Contenedor con Scrollbar
        self.canvas = tk.Canvas(frame_lista)
        scrollbar = ttk.Scrollbar(frame_lista, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Panel de Acciones ---
        frame_acciones = ttk.LabelFrame(self.root, text=" 3. Enviar Orden ")
        frame_acciones.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame_acciones, text="⚡ Apagar", command=lambda: self.confirmar_accion("apagar")).pack(side="left", expand=True, padx=5, pady=5)
        ttk.Button(frame_acciones, text="🔄 Reiniciar", command=lambda: self.confirmar_accion("reiniciar")).pack(side="left", expand=True, padx=5, pady=5)
        ttk.Button(frame_acciones, text="🕒 Sincronitzar Hora (Host)", command=lambda: self.confirmar_accion("hora")).pack(side="left", expand=True, padx=5, pady=5)
        ttk.Button(frame_acciones, text="📅 Posar al dia", command=lambda: self.confirmar_accion("actualizar")).pack(side="left", expand=True, padx=5, pady=5)

    # --- Persistencia JSON ---
    def guardar_dispositivos(self):
        try:
            with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
                json.dump(self.dispositivos, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No s'ha pogut guardar en l'arxiu:\n{e}")
            return False

    def fuerza_guardado_manual(self):
        if self.guardar_dispositivos():
            messagebox.showinfo("Guardado", f"Nombres i llistes guardades amb èxit a:\n{ARCHIVO_CONFIG}")

    def cargar_dispositivos_guardados(self):
        if os.path.exists(ARCHIVO_CONFIG):
            try:
                with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    
                for ip, val in datos.items():
                    if isinstance(val, str):
                        self.dispositivos[ip] = {"alias": val, "hostname": "Desconegut"}
                    else:
                        self.dispositivos[ip] = val
                        
                self.actualizar_lista_ui()
                self.lbl_estado.config(text=f"Cargados {len(self.dispositivos)} dispositius.")
            except Exception as e:
                self.dispositivos = {}

    def limpiar_guardados(self):
        if messagebox.askyesno("Confirmar", "¿Desitjes borrar la llista guardada de dispositius?"):
            self.dispositivos.clear()
            self.guardar_dispositivos()
            self.actualizar_lista_ui()
            self.lbl_estado.config(text="Llista llimpiada.")

    # --- Escaneo de Red ---
    def obtener_hostname(self, ip):
        try:
            nombre, _, _ = socket.gethostbyaddr(ip)
            return nombre
        except Exception:
            return "No detectado"

    def ping_ip(self, ip):
        comando = ["ping", "-n", "1", "-w", "500", ip]
        resultado = subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if resultado.returncode == 0:
            hostname_detectado = self.obtener_hostname(ip)
            if ip not in self.dispositivos:
                self.dispositivos[ip] = {
                    "alias": f"Equipo ({ip.split('.')[-1]})",
                    "hostname": hostname_detectado
                }
            else:
                self.dispositivos[ip]["hostname"] = hostname_detectado

    def iniciar_escaneo(self):
        self.btn_escanear.config(state="disabled")
        self.lbl_estado.config(text="Escaneando red...")
        threading.Thread(target=self.escanear_red, daemon=True).start()

    def escanear_red(self):
        subred = self.subred_var.get().strip()
        hilos = []

        for i in range(1, 255):
            ip = f"{subred}.{i}"
            hilo = threading.Thread(target=self.ping_ip, args=(ip,))
            hilos.append(hilo)
            hilo.start()

        for hilo in hilos:
            hilo.join()

        self.guardar_dispositivos()
        self.root.after(0, self.actualizar_lista_ui)

    # --- Renderizado ---
    def actualizar_lista_ui(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        ips_ordenadas = sorted(self.dispositivos.keys(), key=lambda x: [int(i) for i in x.split('.')])

        if not ips_ordenadas:
            ttk.Label(self.scroll_frame, text="No hi ha dispositius registrats. Realitza un escaneig.").pack(padx=10, pady=10)
        else:
            for ip in ips_ordenadas:
                frame_item = ttk.Frame(self.scroll_frame)
                frame_item.pack(fill="x", anchor="w", padx=5, pady=3)

                var = tk.BooleanVar()
                chk = ttk.Checkbutton(frame_item, variable=var)
                chk.pack(side="left", padx=(5, 10))

                alias_var = tk.StringVar(value=self.dispositivos[ip].get("alias", ""))
                entry_alias = ttk.Entry(frame_item, textvariable=alias_var, width=28)
                entry_alias.pack(side="left", padx=5)

                entry_alias.bind("<FocusOut>", lambda event, target_ip=ip, a_var=alias_var: self.guardar_alias(target_ip, a_var.get()))
                entry_alias.bind("<Return>", lambda event, target_ip=ip, a_var=alias_var: self.guardar_alias(target_ip, a_var.get()))

                lbl_ip = ttk.Label(frame_item, text=ip, width=16, font=('Courier', 10))
                lbl_ip.pack(side="left", padx=5)

                hostname = self.dispositivos[ip].get("hostname", "No detectado")
                lbl_hostname = ttk.Label(frame_item, text=hostname, foreground="#555555")
                lbl_hostname.pack(side="left", padx=5)

                self.check_vars[ip] = var

        self.btn_escanear.config(state="normal")
        self.lbl_estado.config(text=f"Llista actualitzada. Total: {len(self.dispositivos)} equips.")

    def guardar_alias(self, ip, nuevo_alias):
        if ip in self.dispositivos:
            self.dispositivos[ip]["alias"] = nuevo_alias
            self.guardar_dispositivos()

    def seleccionar_todos(self, estado):
        for var in self.check_vars.values():
            var.set(estado)

    # --- Envío de Comandos Modificados ---
    def obtener_ips_seleccionadas(self):
        return [ip for ip, var in self.check_vars.items() if var.get()]

    def confirmar_accion(self, accion):
        seleccionados = self.obtener_ips_seleccionadas()
        if not seleccionados:
            messagebox.showwarning("Atenció", "Has de seleccionar almenys un ordinador.")
            return

        if messagebox.askyesno("Confirmar", f"¿Deseas ejecutar '{accion}' en {len(seleccionados)} ordenador(es)?"):
            threading.Thread(target=self.ejecutar_comandos, args=(accion, seleccionados), daemon=True).start()

    def ejecutar_comandos(self, accion, ips):
        # 1. Obtener la fecha y hora exactas del ordenador Host actual
        ahora_host = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for ip in ips:
            if accion == "apagar":
                cmd = f"shutdown /m \\\\{ip} /s /f /t 0"
                
            elif accion == "reiniciar":
                cmd = f"shutdown /m \\\\{ip} /r /f /t 0"
                
            elif accion == "hora":
                # Forzar la fecha/hora del Host en el equipo objetivo usando PowerShell remoto
                script_hora = f"Set-Date -Date '{ahora_host}'"
                cmd = f'powershell -Command "Invoke-Command -ComputerName {ip} -ScriptBlock {{ {script_hora} }}"'
                
            elif accion == "actualizar":
                # Comando 'Poner al Día': Busca, descarga e instala parches en Win 7, 10 y 11
                script_actualizar = (
                    "if (Get-Command USOClient -ErrorAction SilentlyContinue) { "
                    "   USOClient StartInteractiveScan; USOClient StartDownload; USOClient StartInstall "
                    "} else { "
                    "   wuauclt /detectnow /updatenow "
                    "}"
                )
                cmd = f'powershell -Command "Invoke-Command -ComputerName {ip} -ScriptBlock {{ {script_actualizar} }}"'

            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.root.after(0, lambda: messagebox.showinfo("Éxito", f"Orden '{accion}' enviada correctamente a los equipos."))

if __name__ == "__main__":
    root = tk.Tk()
    app = RedControlApp(root)
    root.mainloop()