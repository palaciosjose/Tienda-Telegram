#!/usr/bin/env python3
"""
Script para revisar y ajustar la configuración existente de Binance
"""

import sqlite3
import os

def check_existing_config():
    """Revisar configuración actual"""
    print("🔍 REVISANDO CONFIGURACIÓN ACTUAL DE BINANCE")
    print("=" * 50)
    
    if not os.path.exists('data/db/main_data.db'):
        print("❌ ERROR: Base de datos no encontrada")
        return None
    
    try:
        conn = sqlite3.connect('data/db/main_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT api_key, api_secret, merchant_id FROM binance_data;")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            api_key, api_secret, merchant_id = result
            
            print("✅ CONFIGURACIÓN ENCONTRADA:")
            print(f"🔑 API Key: {api_key[:10]}..." if api_key else "❌ API Key: No configurado")
            print(f"🔐 API Secret: {api_secret[:10]}..." if api_secret else "❌ API Secret: No configurado")
            print(f"🏪 Merchant ID: {merchant_id}" if merchant_id else "❌ Merchant ID: No configurado")
            
            return result
        else:
            print("❌ No hay configuración de Binance")
            return None
            
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")
        return None

def analyze_config(api_key, api_secret, merchant_id):
    """Analizar la configuración actual"""
    print("\n🔍 ANÁLISIS DE LA CONFIGURACIÓN:")
    print("=" * 40)
    
    issues = []
    
    # Verificar API Key
    if api_key and len(api_key) > 20:
        print("✅ API Key: Formato correcto")
    else:
        print("⚠️ API Key: Posible problema de formato")
        issues.append("api_key")
    
    # Verificar API Secret
    if api_secret and len(api_secret) > 20:
        print("✅ API Secret: Formato correcto")
    else:
        print("⚠️ API Secret: Posible problema de formato")
        issues.append("api_secret")
    
    # Verificar Merchant ID / Wallet Address
    if merchant_id:
        if merchant_id.isdigit():
            print(f"🔶 Merchant ID: {merchant_id} (ID numérico)")
            print("ℹ️ Esto podría ser un ID de merchant, no una wallet address")
            issues.append("wallet_address")
        elif merchant_id.startswith('0x') or len(merchant_id) > 20:
            print(f"✅ Wallet Address: {merchant_id[:15]}...")
        else:
            print(f"⚠️ Merchant ID/Wallet: {merchant_id} (formato unclear)")
            issues.append("wallet_address")
    else:
        print("❌ Merchant ID/Wallet: No configurado")
        issues.append("wallet_address")
    
    return issues

def test_payment_flow():
    """Mostrar cómo se ve el flujo de pago actual"""
    print("\n📱 FLUJO DE PAGO ACTUAL:")
    print("=" * 30)
    
    try:
        import dop
        binance_data = dop.get_binancedata()
        
        if binance_data:
            api_key, api_secret, merchant_id = binance_data
            
            print("Cuando un cliente selecciona Binance Pay, ve esto:")
            print()
            print("💳 **Pago con Binance Pay**")
            print()
            print("📦 **Producto:** Ejemplo")
            print("🔢 **Cantidad:** 1")
            print("💰 **Total:** $10 USD")
            print()
            print("🚀 **Instrucciones de pago:**")
            print()
            print("1️⃣ Abre tu app de **Binance**")
            print("2️⃣ Ve a **'Pay'** → **'Enviar'**")
            print(f"3️⃣ Envía **$10 USD** a: `{merchant_id}`")
            print()
            print("⚠️ **PROBLEMA DETECTADO:**")
            
            if merchant_id and merchant_id.isdigit():
                print(f"• El campo tiene: {merchant_id} (parece ser un Merchant ID)")
                print("• Pero necesitas: Una wallet address de Binance")
                print("• Ejemplo correcto: 0x742d35Cc6634C0532925a3b8D404bBf...")
                print()
                print("🔧 **SOLUCIÓN:** Necesitas configurar tu wallet address real")
            else:
                print("• Configuración parece correcta")
                
        else:
            print("❌ No se pudo leer la configuración")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def fix_wallet_address():
    """Corregir la wallet address"""
    print("\n🔧 CORREGIR WALLET ADDRESS")
    print("=" * 30)
    
    print("🎯 NECESITAS:")
    print("• Tu wallet address personal de Binance")
    print("• NO es el Merchant ID")
    print("• Es donde recibes criptomonedas")
    print()
    print("📍 CÓMO ENCONTRAR TU WALLET ADDRESS:")
    print("1. Abre Binance app/web")
    print("2. Ve a 'Wallet' → 'Overview'")
    print("3. Selecciona una criptomoneda (ej: USDT)")
    print("4. Toca 'Deposit'")
    print("5. Copia la dirección que aparece")
    print()
    
    current_config = check_existing_config()
    if current_config:
        api_key, api_secret, merchant_id = current_config
        print(f"💡 Actualmente tienes: {merchant_id}")
        print()
    
    choice = input("¿Quieres actualizar tu wallet address? (s/n): ").lower().strip()
    
    if choice.startswith('s'):
        print("\n📝 IMPORTANTE:")
        print("• La wallet address empieza con 0x (para ETH/BSC)")
        print("• O con otros prefijos según la red")
        print("• Ejemplo: 0x742d35Cc6634C0532925a3b8D404bBf...")
        print()
        
        new_wallet = input("Ingresa tu wallet address de Binance: ").strip()
        
        if new_wallet and len(new_wallet) > 10:
            # Actualizar solo el wallet address, mantener API keys
            try:
                conn = sqlite3.connect('data/db/main_data.db')
                cursor = conn.cursor()
                
                if current_config:
                    # Mantener API keys existentes, solo cambiar wallet
                    cursor.execute("UPDATE binance_data SET merchant_id = ? WHERE rowid = 1", (new_wallet,))
                else:
                    # Crear nueva entrada solo con wallet
                    cursor.execute("INSERT INTO binance_data VALUES(?, ?, ?)", ("", "", new_wallet))
                
                conn.commit()
                conn.close()
                
                print("✅ Wallet address actualizada!")
                print(f"📍 Nueva wallet: {new_wallet}")
                
                return True
                
            except Exception as e:
                print(f"❌ Error actualizando: {e}")
                return False
        else:
            print("❌ Wallet address inválida")
            return False
    else:
        print("ℹ️ Configuración mantenida sin cambios")
        return False

def show_recommendations():
    """Mostrar recomendaciones"""
    print("\n💡 RECOMENDACIONES:")
    print("=" * 20)
    
    current_config = check_existing_config()
    if current_config:
        api_key, api_secret, merchant_id = current_config
        issues = analyze_config(api_key, api_secret, merchant_id)
        
        if not issues:
            print("✅ Tu configuración está completa")
            print("✅ Solo actualiza el payments.py para seguridad")
        else:
            if "wallet_address" in issues:
                print("🔶 CRÍTICO: Configura tu wallet address real")
                print("   - Sin esto, los clientes no saben dónde enviar dinero")
            
            if "api_key" in issues or "api_secret" in issues:
                print("🔶 OPCIONAL: Las API keys están para verificación automática")
                print("   - Puedes usar verificación manual sin ellas")
    
    print("\n🚀 SIGUIENTE PASO:")
    print("1. Actualiza payments.py con el código de seguridad")
    print("2. Agrega los callbacks a main.py")
    print("3. Reinicia el bot")

def main():
    """Función principal"""
    print("🔍 VERIFICADOR DE CONFIGURACIÓN BINANCE")
    print("Este script revisa tu configuración actual")
    print()
    
    # Revisar configuración actual
    current_config = check_existing_config()
    
    if current_config:
        api_key, api_secret, merchant_id = current_config
        
        # Analizar configuración
        issues = analyze_config(api_key, api_secret, merchant_id)
        
        # Mostrar flujo de pago
        test_payment_flow()
        
        # Ofrecer corrección si hay problemas
        if "wallet_address" in issues:
            print("\n⚠️ PROBLEMA DETECTADO: Wallet address necesita corrección")
            fix_wallet_address()
        
        # Mostrar recomendaciones
        show_recommendations()
        
    else:
        print("\n❌ No se encontró configuración de Binance")
        print("Ejecuta el setup desde el bot: /adm → Configuración de pago")

if __name__ == '__main__':
    main()