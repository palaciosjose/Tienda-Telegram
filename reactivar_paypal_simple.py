#!/usr/bin/env python3

def reactivar():
    print("REACTIVANDO PAYPAL...")
    
    with open('payments.py', 'r') as f:
        content = f.read()
    
    if 'PAYPAL DESHABILITADO' in content:
        # Remover líneas de deshabilitación
        lines = content.split('\n')
        new_lines = []
        skip = False
        
        for line in lines:
            if 'PAYPAL DESHABILITADO' in line:
                skip = True
            elif 'FIN DESHABILITACION' in line:
                skip = False
                continue
            elif not skip:
                new_lines.append(line)
        
        with open('payments.py', 'w') as f:
            f.write('\n'.join(new_lines))
        
        # Habilitar en config
        try:
            import shelve
            with shelve.open('data/bd/payments_bd.bd') as bd:
                bd['paypal'] = '✅'
            print("PAYPAL REACTIVADO!")
        except:
            print("PAYPAL código limpiado - habilita manualmente en /adm")
    else:
        print("PayPal no estaba deshabilitado")

if __name__ == '__main__':
    reactivar()
