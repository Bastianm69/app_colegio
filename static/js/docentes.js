function mostrarOcultarPassword() {
    const inputPass = document.getElementById('inputPassword');
    const iconoOjo = document.getElementById('icono-ojo');
    const iconoOjoCerrado = document.getElementById('icono-ojo-cerrado');

    if (inputPass.type === 'password') {
        // Al mostrar la contraseña (tipo text)
        inputPass.type = 'text';
        iconoOjo.style.display = 'block';          // Muestra el ojo abierto (Estado: "estoy viendo")
        iconoOjoCerrado.style.display = 'none';    // Esconde el ojo tachado
    } else {
        // Al ocultar la contraseña (tipo password)
        inputPass.type = 'password';
        iconoOjo.style.display = 'none';           // Esconde el ojo abierto
        iconoOjoCerrado.style.display = 'block';   // Muestra el ojo tachado (Estado: "está oculto")
    }
}