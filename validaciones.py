def validar_rut(rut):
    # 1. Limpiamos el RUT (quitamos puntos y el guion) y lo pasamos a mayúsculas
    rut_limpio = rut.replace(".", "").replace("-", "").upper()
    
    # Si es muy corto, es inválido
    if len(rut_limpio) < 2:
        return False
        
    cuerpo = rut_limpio[:-1]
    dv_ingresado = rut_limpio[-1]
    
    # El cuerpo solo debe contener números
    if not cuerpo.isdigit():
        return False
        
    # 2. Algoritmo Módulo 11
    suma = 0
    multiplo = 2
    
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2
        
    dv_esperado = 11 - (suma % 11)
    
    # 3. Asignamos el dígito verificador correspondiente
    if dv_esperado == 11:
        dv_esperado = '0'
    elif dv_esperado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_esperado)
        
    # 4. Comparamos el que calculamos con el que ingresó el usuario
    return dv_ingresado == dv_esperado