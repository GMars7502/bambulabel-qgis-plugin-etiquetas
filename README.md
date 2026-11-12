# BambuLabel Studio v1.2 — Plugin de Etiquetado y Digitalización para QGIS

**BambuLabel Studio** es un complemento (*plugin*) especializado desarrollado en PyQGIS para optimizar y acelerar la delimitación de manchales y copas de bambú sobre ortomosaicos GeoTIFF de dron de gran escala (gigapíxeles).

---

## 1. Novedades y Herramientas de la Versión 1.2

### 1. Polígono Lineal Directo (Estilo Nativo QGIS)
* **Digitalización precisa sin círculos:** Permite crear polígonos con bordes rectos directos entre vértices (clic a clic), exactamente como la herramienta nativa de polígonos de QGIS, sin buffers circulares indeseados.
* **Previsualización en tiempo real:** Muestra una banda elástica semitransparente que se conecta dinámicamente con el puntero del ratón conforme se van agregando vértices.
* **Finalización:** Se finaliza con un **clic derecho**, **doble clic** o pulsando **Enter**.

### 2. Auto-Relleno de Centros y Huecos (Efecto Dona / Delineado de Árbol)
* Casilla de verificación: **`☑️ Rellenar centro automáticamente (Efecto dona / árbol)`**.
* **Cómo funciona:** Cuando delineas únicamente el contorno exterior de una copa de árbol o realizas un trazado cerrado con forma de dona dejando el centro vacío, el algoritmo descarta automáticamente los huecos interiores (`poly[1:]`) y rellena el 100% del centro sólido como un único polígono limpio.
* **Ahorro de tiempo:** Evita tener que pintar o colorear todo el interior del manchal; basta con recorrer el borde perimetral.

### 3. Ventana Emergente de Confirmación y Edición de Atributos al Terminar
* **Revisión inmediata antes de guardar:** Al terminar de delinear la figura (clic derecho, doble clic o Enter), se abre automáticamente una ventana emergente: **Confirmar Nueva Etiqueta**.
* **Datos calculados en pantalla:**
  * **Superficie calculada:** Muestra el área exacta en $m^2$ y en hectáreas ($ha$).
  * **Perímetro:** Muestra la longitud del borde en metros ($m$).
* **Campos editables con memoria inteligente:**
  * **`id`:** Autoincrementado automáticamente con el número correlativo (editable si deseas asignar otro número).
  * **`Imagen`:** Desplegable con todos los archivos GeoTIFF cargados en el proyecto QGIS, permitiendo tanto **seleccionar un TIFF** de la lista como **escribir libremente cualquier nombre**. El plugin memoriza la imagen para los siguientes trazos.
  * **`Superficie`:** Campo numérico prellenado con el cálculo geométrico en $m^2$ (editable si se desea redondear o ajustar).
* **Decisión en un solo clic o teclado:**
  * **`✅ Aceptar y Cargar (Enter)`**: Guarda la etiqueta en la capa con los datos confirmados.
  * **`❌ Cancelar (Esc)`**: Descarta el polígono dibujado por completo sin guardarlo en el shapefile.
* **Casilla opcional en el panel:** `☑️ Mostrar ventana de atributos al terminar figura` (activa por defecto). Permite desactivarla temporalmente si se prefiere digitalizar en ráfaga masiva.

### 4. Deshacer Clic a Clic Durante el Trazado (Vértice por Vértice)
* Si vas por el 4to o 5to clic y cometes un error en el último punto colocado:
  * Presiona la tecla **`Backspace`** (Retroceso) o **`Ctrl + Z`**.
  * O haz clic en el botón del panel: **`↩️ Deshacer último clic (Puntos actuales: N)`**.
* **Resultado:** Elimina únicamente el último vértice trazado, permitiéndote corregir la trayectoria sin perder el resto del polígono ni tener que empezar de cero.

### 4. Pinceles Especiales con Anti-Tambaleo
* 🖌️ **Pincel por Flujo (*Streaming*):** Permite pintar a mano alzada manteniendo presionado el ratón. Incluye filtro de suavizado (media móvil) con 5 niveles ajustables (`0` a `4`) para amortiguar el temblor natural de la mano.
* 📏 **Pincel por Tramos Gruesos:** Trazado punto a punto aplicando un ancho de franja uniforme en metros.
* 🧹 **Borrador Inteligente:** Permite recortar o sustraer áreas de polígonos ya creados simplemente pasando sobre ellos.

### 5. Respeto Estricto de Atributos del Usuario
* **Cero imposición de columnas ajenas:** El plugin respeta exactamente tus columnas: `id`, `Imagen`, `Superficie` (o las que contenga tu capa activa).
* **Autocompletado inteligente:**
  * `id`: Incremento numérico automático correlativo.
  * `Imagen`: Asigna en tiempo real el nombre del GeoTIFF activo sobre el que estás trabajando.
  * `Superficie`: Calcula automáticamente el área exacta en metros cuadrados ($m^2$) de cada geometría.

---

## 2. Guía Rápida de Uso

### Paso 1: Recargar el plugin en QGIS
1. En QGIS, dirígete a: **Complementos** ➔ **Administrar e instalar complementos...**
2. En la pestaña **Instalados**, desmarca y vuelve a marcar **`BambuLabel - Pincel y Gestión de Etiquetas`** para refrescar a la versión 1.2.

### Paso 2: Cargar o crear la capa de trabajo
* **Cargar tu capa actual:** Clic en **`📂 Cargar SHP`** (ej. `Manchal_Bambu.shp`, `cocani80msm_rgb.shp`). Reconocerá automáticamente tus campos `id, Imagen, Superficie`.
* **Crear nueva capa:** Clic en **`➕ Nueva Capa (.shp)`**.

### Paso 3: Elegir el modo de dibujo
1. **Para delinear copas con precisión:** Selecciona **`Polígono Lineal`**.
   * Haz clic en cada borde de la copa.
   * Si te equivocas en un punto: pulsa **`Backspace`** o **`Ctrl + Z`**.
   * Con la casilla **`Rellenar centro automáticamente`** activada, solo recorre el contorno y haz **clic derecho**: el interior se rellenará solo.
2. **Para trazos rápidos a mano alzada:** Selecciona **`Pincel Flujo`** y ajusta el **Suavizado** en nivel 2.
3. **Para borrar excedentes:** Selecciona **`Borrador`**.

### Paso 4: Inspección y guardado
* La tabla del panel lista todas las etiquetas con su `id`, `Imagen` y `Superficie (m²)`.
* Haz **doble clic** sobre cualquier fila para hacer zoom inmediato a esa etiqueta.
* Haz clic en **`💾 Guardar Cambios en Disco`** para consolidar el archivo Shapefile.

