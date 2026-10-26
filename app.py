import datetime
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Control de Trading - Opciones Binarias",
    page_icon="📈",
    layout="wide",
)


def get_connection():
    conn = sqlite3.connect("trading_journal.db", check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            saldo_inicial REAL,
            saldo_actual REAL,
            pct_meta REAL,
            pct_operacion REAL,
            limite_ops INTEGER DEFAULT 3
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER,
            fecha TEXT,
            saldo_inicial REAL,
            meta_monto REAL,
            monto_operacion REAL,
            ganadas INTEGER,
            perdidas INTEGER,
            resultado_monto REAL,
            saldo_final REAL,
            estado_disciplina TEXT,
            nota_emocional TEXT,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
        )
    """
    )
    # Migraciones seguras por si la tabla ya existía
    try:
        c.execute("ALTER TABLE cuentas ADD COLUMN limite_ops INTEGER DEFAULT 3")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute(
            "ALTER TABLE sesiones ADD COLUMN estado_disciplina TEXT DEFAULT 'Plan Respetado'"
        )
        c.execute(
            "ALTER TABLE sesiones ADD COLUMN nota_emocional TEXT DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass

    # Dejar solo una cuenta por defecto con límite de 3 operaciones
    c.execute(
        "INSERT OR IGNORE INTO cuentas (id, nombre, saldo_inicial, saldo_actual, pct_meta, pct_operacion, limite_ops) VALUES (1, 'Cuenta Principal', 10.0, 10.0, 5.0, 3.0, 3)"
    )
    conn.commit()
    conn.close()


init_db()

st.title("📈 Bitácora de Trading - Opciones Binarias")

conn = get_connection()
df_cuentas = pd.read_sql_query("SELECT * FROM cuentas", conn)

# --- BARRA LATERAL: GESTIÓN DE CUENTAS ---
st.sidebar.header("⚙️ Gestión de Cuentas")

cuenta_seleccionada = st.sidebar.selectbox(
    "Selecciona la cuenta activa:", df_cuentas["nombre"]
)

cuenta_info = df_cuentas[df_cuentas["nombre"] == cuenta_seleccionada].iloc[0]
cuenta_id = int(cuenta_info["id"])
saldo_actual = float(cuenta_info["saldo_actual"])
pct_meta = float(cuenta_info["pct_meta"])
pct_operacion = float(cuenta_info["pct_operacion"])
limite_ops_actual = int(
    cuenta_info["limite_ops"] if "limite_ops" in cuenta_info else 3
)

with st.sidebar.expander("➕ Agregar Nueva Cuenta"):
    with st.form("form_nueva_cuenta"):
        nuevo_nombre = st.text_input("Nombre de la cuenta")
        saldo_base_nueva = st.number_input("Saldo Inicial ($)", value=10.0, step=1.0)
        meta_nueva = st.number_input("% Meta por Sesión", value=5.0, step=0.5)
        op_nueva = st.number_input("% Inversión por Operación", value=3.0, step=0.5)
        limite_nuevo = st.number_input(
            "Límite Máx. de Operaciones por Sesión",
            min_value=1,
            value=3,
            step=1,
        )
        btn_crear_cuenta = st.form_submit_button("Crear Cuenta")

        if btn_crear_cuenta and nuevo_nombre:
            try:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO cuentas (nombre, saldo_inicial, saldo_actual, pct_meta, pct_operacion, limite_ops)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        nuevo_nombre,
                        saldo_base_nueva,
                        saldo_base_nueva,
                        meta_nueva,
                        op_nueva,
                        limite_nuevo,
                    ),
                )
                conn.commit()
                st.success(f"¡Cuenta '{nuevo_nombre}' creada con éxito!")
                st.rerun()
            except Exception as e:
                st.error("Ese nombre de cuenta ya existe.")

with st.sidebar.expander("✏️ Editar Cuenta Activa"):
    nuevo_saldo = st.number_input(
        "Ajustar Saldo Actual ($)", value=saldo_actual, step=1.0
    )
    nuevo_pct_meta = st.number_input(
        "% Meta por Sesión", value=pct_meta, step=0.5
    )
    nuevo_pct_op = st.number_input(
        "% Inversión por Operación", value=pct_operacion, step=0.5
    )
    nuevo_limite_ops = st.number_input(
        "Límite Máx. de Operaciones",
        min_value=1,
        value=limite_ops_actual,
        step=1,
    )

    if st.button("Guardar Cambios de Cuenta"):
        c = conn.cursor()
        c.execute(
            """
            UPDATE cuentas 
            SET saldo_actual = ?, pct_meta = ?, pct_operacion = ?, limite_ops = ?
            WHERE id = ?
        """,
            (
                nuevo_saldo,
                nuevo_pct_meta,
                nuevo_pct_op,
                nuevo_limite_ops,
                cuenta_id,
            ),
        )
        conn.commit()
        st.sidebar.success("¡Parámetros actualizados!")
        st.rerun()

# --- CÁLCULO DE METAS ---
ganancia_meta_dolares = saldo_actual * (pct_meta / 100.0)
saldo_meta_total = saldo_actual + ganancia_meta_dolares
monto_por_op = saldo_actual * (pct_operacion / 100.0)

# Resaltar visualmente el nombre de la cuenta activa en la cabecera
st.markdown(
    f"### 📊 Panel Activo: <span style='color:#FF4B4B;'>{cuenta_seleccionada}</span>",
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Saldo Actual", f"${saldo_actual:.2f}")
col2.metric(
    f"Meta de Sesión ({pct_meta}%)",
    f"${saldo_meta_total:.2f}",
    delta=f"+${ganancia_meta_dolares:.2f}",
)
col3.metric(f"Inversión por Trade ({pct_operacion}%)", f"${monto_por_op:.2f}")
col4.metric("Límite de Ops / Sesión", f"{limite_ops_actual} trades")

st.divider()

# --- PESTAÑAS DE NAVEGACIÓN ---
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📝 Registrar Sesión",
        "📊 Historial y Estadísticas",
        "📈 Proyección de Interés Compuesto",
        "⚙️ Gestionar / Borrar Registros",
    ]
)

with tab1:
    st.subheader("Formulario de Cierre de Sesión y Control de Disciplina")
    st.info(
        f"💡 Saldo actual: **${saldo_actual:.2f}** | Meta del **{pct_meta}%**: **${saldo_meta_total:.2f}** (+${ganancia_meta_dolares:.2f}). Límite aconsejado: **{limite_ops_actual} operaciones**."
    )

    with st.form("form_sesion"):
        fecha_sesion = st.date_input("Fecha", datetime.date.today())
        cols_form1, cols_form2 = st.columns(2)

        with cols_form1:
            operaciones_ganadas = st.number_input(
                "Operaciones Ganadas (ITM)", min_value=0, value=0, step=1
            )
        with cols_form2:
            operaciones_perdidas = st.number_input(
                "Operaciones Perdidas (OTM)", min_value=0, value=0, step=1
            )

        resultado_neto = st.number_input(
            "Ganancia / Pérdida Neta Final ($)",
            value=0.0,
            step=0.5,
            help="Coloca valor positivo si ganaste o negativo si quedaste en pérdida",
        )

        nota_emocional = st.text_input(
            "📝 Nota Psicológica / Emocional (Ej. Sesión limpia, respeté el plan...)",
            value="",
        )

        btn_guardar = st.form_submit_button("💾 Guardar Registro de Sesión")

    if btn_guardar:
        total_ops_sesion = operaciones_ganadas + operaciones_perdidas
        if total_ops_sesion <= limite_ops_actual:
            estado_disc = "✅ Plan Respetado"
        else:
            estado_disc = "⚠️ Sobreoperativa"

        nuevo_saldo_final = saldo_actual + resultado_neto
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO sesiones (cuenta_id, fecha, saldo_inicial, meta_monto, monto_operacion, ganadas, perdidas, resultado_monto, saldo_final, estado_disciplina, nota_emocional)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cuenta_id,
                str(fecha_sesion),
                saldo_actual,
                ganancia_meta_dolares,
                monto_por_op,
                operaciones_ganadas,
                operaciones_perdidas,
                resultado_neto,
                nuevo_saldo_final,
                estado_disc,
                nota_emocional,
            ),
        )

        c.execute(
            "UPDATE cuentas SET saldo_actual = ? WHERE id = ?",
            (nuevo_saldo_final, cuenta_id),
        )

        conn.commit()
        st.success(
            f"¡Sesión guardada! Estado: {estado_disc} | Nuevo saldo: ${nuevo_saldo_final:.2f}"
        )
        st.rerun()

with tab2:
    st.subheader(f"Avance y Estadísticas de {cuenta_seleccionada}")

    df_sesiones = pd.read_sql_query(
        f"SELECT * FROM sesiones WHERE cuenta_id = {cuenta_id} ORDER BY id ASC",
        conn,
    )

    if df_sesiones.empty:
        st.info("Aún no hay sesiones registradas para esta cuenta.")
    else:
        fig_curva = px.line(
            df_sesiones,
            x=df_sesiones.index + 1,
            y="saldo_final",
            markers=True,
            title=f"Curva de Crecimiento - {cuenta_seleccionada}",
            labels={"x": "Número de Sesión", "saldo_final": "Saldo ($)"},
        )
        st.plotly_chart(fig_curva, use_container_width=True)

        total_trades = (
            df_sesiones["ganadas"].sum() + df_sesiones["perdidas"].sum()
        )
        total_itm = df_sesiones["ganadas"].sum()
        winrate = (total_itm / total_trades * 100) if total_trades > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Sesiones Ejecutadas", len(df_sesiones))
        m2.metric("Total Operaciones", total_trades)
        m3.metric("Win Rate (Efectividad)", f"{winrate:.1f}%")

        st.write("### Tabla de Historial y Disciplina")
        st.dataframe(
            df_sesiones[
                [
                    "fecha",
                    "saldo_inicial",
                    "ganadas",
                    "perdidas",
                    "resultado_monto",
                    "saldo_final",
                    "estado_disciplina",
                    "nota_emocional",
                ]
            ],
            use_container_width=True,
        )

with tab3:
    st.subheader(
        f"📈 Proyección Teórica de Interés Compuesto ({cuenta_seleccionada})"
    )
    st.info(
        f"Proyección sesión a sesión partiendo de tu capital actual (**${saldo_actual:.2f}**) cumpliendo la meta del **{pct_meta}%**."
    )

    num_sesiones_proyeccion = st.slider(
        "Número de sesiones a proyectar:", 10, 100, 30
    )

    datos_proyeccion = []
    capital_proyectado = saldo_actual
    for i in range(1, num_sesiones_proyeccion + 1):
        saldo_inicial_s = capital_proyectado
        meta_s = saldo_inicial_s * (pct_meta / 100.0)
        saldo_final_s = saldo_inicial_s + meta_s
        datos_proyeccion.append(
            {
                "Sesión": f"Sesión {i}",
                "Saldo Inicial ($)": round(saldo_inicial_s, 2),
                "Meta Ganancia ($)": round(meta_s, 2),
                "Saldo Final Esperado ($)": round(saldo_final_s, 2),
            }
        )
        capital_proyectado = saldo_final_s

    df_proj = pd.DataFrame(datos_proyeccion)
    st.dataframe(df_proj, use_container_width=True)

with tab4:
    st.subheader("⚙️ Eliminar Registro Erróneo")
    st.warning("⚠️ Selecciona y elimina cualquier sesión ingresada por error.")

    df_sesiones_borrar = pd.read_sql_query(
        f"SELECT id, fecha, saldo_inicial, resultado_monto, saldo_final FROM sesiones WHERE cuenta_id = {cuenta_id} ORDER BY id DESC",
        conn,
    )

    if df_sesiones_borrar.empty:
        st.info("No hay registros para eliminar en esta cuenta.")
    else:
        sesion_a_borrar = st.selectbox(
            "Selecciona la sesión que deseas eliminar:",
            df_sesiones_borrar.apply(
                lambda row: f"ID: {row['id']} | Fecha: {row['fecha']} | Resultado: ${row['resultado_monto']}",
                axis=1,
            ),
        )

        if st.button("🗑️ Eliminar Sesión Seleccionada", type="primary"):
            id_extraido = int(
                sesion_a_borrar.split("|")[0].replace("ID:", "").strip()
            )

            c = conn.cursor()
            c.execute("DELETE FROM sesiones WHERE id = ?", (id_extraido,))
            conn.commit()
            st.success(
                f"¡Sesión ID {id_extraido} eliminada correctamente! Recuerda verificar tu saldo actual en la barra lateral."
            )
            st.rerun()

conn.close()
