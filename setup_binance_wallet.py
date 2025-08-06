#!/usr/bin/env python3
"""
Script para configurar correctamente el wallet de Binance
"""

import sqlite3
import os

def setup_binance_wallet():
    """Configurar wallet de Binance"""
    print("🔧 CONFIGURACIÓN DE BINANCE WALLET")
    print("=" * 50)
    
    # Verificar base de datos
    if not os.path.exists('data/db/main_data.db'):
        print("❌ ERROR: Base de datos no encontrada")
        return False
    
    print("Para recibir pagos con Binance necesitas:")
    print("1. 📱 Tu wallet address de Binance")
    print("2. 🔑 API Key y Secret (opcional, para verificación automática)")
    print()
    
    # Solicitar wallet address
    print("📍 WALLET ADDRESS:")
    print("Esta es la dirección donde recibirás los pagos.")
    print("Ejemplo: 0x742d35Cc6634C0532925a3b8D404bBf...")
    print()
    
    wallet_address = input("Ingresa tu Binance wallet address: ").strip()
    
    if not wallet_address:
        print("❌ ERROR: Wallet address es requerido")
        return False
    
    # Preguntar por API credentials (opcional)
    print("\n🔑 API CREDENTIALS (OPCIONAL):")
    print("Si tienes API Key y Secret, puedes habilitarlos para verificación automática.")
    print("Si no los tienes, puedes usar verificación manual.")
    print()
    
    use_api = input("¿Tienes API Key y Secret de Binance? (s/n): ").lower().startswith('s')
    
    api_key = ""
    api_secret = ""
    
    if use_api:
        print("\n📋 Obtén tus credenciales en:")
        print("https://www.binance.com/en/my/settings/api-management")
        print()
        
        api_key = input("API Key: ").strip()
        api_secret = input("API Secret: ").strip()
        
        if not api_key or not api_secret:
            print("⚠️ ADVERTENCIA: API credentials incompletos, usando solo wallet address")
            api_key = ""
            api_secret = ""
    
    # Guardar en base de datos
    try:
        conn = sqlite3.connect('data/db/main_data.db')
        cursor = conn.cursor()
        
        # Eliminar configuración anterior
        cursor.execute("DELETE FROM binance_data")
        
        # Insertar nueva configuración
        # Usamos merchant_id para guardar el wallet address
        cursor.execute("INSERT INTO binance_data VALUES(?, ?, ?)", 
                      (api_key, api_secret, wallet_address))
        
        conn.commit()
        conn.close()
        
        print("\n✅ CONFIGURACIÓN GUARDADA")
        print(f"📍 Wallet: {wallet_address}")
        
        if api_key:
            print(f"🔑 API Key: {api_key[:10]}...")
            print("🤖 Verificación: Automática (cuando esté implementada)")
        else:
            print("🔍 Verificación: Manual por administrador")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR guardando configuración: {e}")
        return False

def test_configuration():
    """Probar la configuración"""
    print("\n🧪 PROBANDO CONFIGURACIÓN...")
    
    try:
        import dop
        binance_data = dop.get_binancedata()
        
        if binance_data:
            api_key, api_secret, wallet_address = binance_data
            print(f"✅ Wallet configurado: {wallet_address}")
            
            if api_key:
                print(f"✅ API Key configurado: {api_key[:10]}...")
            else:
                print("ℹ️ Sin API Key - verificación manual")
            
            return True
        else:
            print("❌ No se encontró configuración")
            return False
            
    except Exception as e:
        print(f"❌ Error probando configuración: {e}")
        return False

def show_payment_instructions():
    """Mostrar instrucciones para el usuario"""
    print("\n📋 INSTRUCCIONES PARA USUARIOS:")
    print("=" * 50)
    
    try:
        import dop
        binance_data = dop.get_binancedata()
        
        if binance_data:
            api_key, api_secret, wallet_address = binance_data
            
            print("Cuando un cliente seleccione Binance Pay verá:")
            print()
            print("🔹 Instrucciones claras de pago")
            print("🔹 Tu wallet address para enviar dinero")
            print("🔹 ID único del pago para seguimiento")
            print("🔹 Botón para confirmar que pagó")
            print()
            print("🔔 PARA TI (ADMINISTRADOR):")
            print("• Recibirás notificación cuando alguien diga que pagó")
            print("• Verificas en tu Binance si llegó el dinero")
            print("• Apruebas o rechazas el pago")
            print("• El cliente recibe su producto automáticamente")
            
        else:
            print("❌ Configura primero tu wallet")
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Función principal"""
    print("🚀 CONFIGURADOR DE BINANCE WALLET")
    print("Este script configurará tu sistema de pagos Binance")
    print()
    
    # Configurar wallet
    if setup_binance_wallet():
        
        # Probar configuración
        if test_configuration():
            
            # Mostrar instrucciones
            show_payment_instructions()
            
            print("\n🎉 ¡CONFIGURACIÓN COMPLETADA!")
            print("\n📋 PRÓXIMOS PASOS:")
            print("1. Reemplaza tu payments.py con el archivo corregido")
            print("2. Actualiza main.py con los nuevos callbacks")
            print("3. Reinicia tu bot: python3 main.py")
            print("4. Prueba un pago de prueba")
            
            print("\n🔔 IMPORTANTE:")
            print("• Los pagos ahora requieren tu aprobación manual")
            print("• Siempre verifica en tu Binance antes de aprobar")
            print("• Mantén activo el bot para recibir notificaciones")
            
        else:
            print("\n❌ Error en la configuración")
    else:
        print("\n❌ Configuración fallida")

if __name__ == '__main__':
    main()