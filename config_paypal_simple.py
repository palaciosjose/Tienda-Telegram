#!/usr/bin/env python3
import sqlite3

def config_paypal():
    print("CONFIGURADOR PAYPAL")
    print("Obtén credenciales en: https://developer.paypal.com")
    
    client_id = input("Client ID: ")
    client_secret = input("Client Secret: ")
    
    if not client_id or not client_secret:
        print("ERROR: Credenciales vacías")
        return
    
    try:
        conn = sqlite3.connect('data/db/main_data.db')
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM paypal_data")
        cursor.execute("INSERT INTO paypal_data VALUES(?, ?, ?)", 
                      (client_id, client_secret, 1))
        
        conn.commit()
        conn.close()
        
        print("GUARDADO!")
        print("Ahora ejecuta: python3 reactivar_paypal_simple.py")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    config_paypal()
