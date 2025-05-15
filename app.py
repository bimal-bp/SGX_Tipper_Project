import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import io
import psycopg2
from psycopg2 import sql
import random

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        host="ep-wild-brook-a49r4hzd-pooler.us-east-1.aws.neon.tech",
        database="neondb",
        user="neondb_owner",
        password="npg_F1vDOg4eumTR",
        sslmode="require"
    )

# Initialize database tables
def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tires table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tires (
        id SERIAL PRIMARY KEY,
        tipper_id VARCHAR(50) NOT NULL,
        tire_number VARCHAR(50) NOT NULL,
        position VARCHAR(50) NOT NULL,
        condition_percent INTEGER NOT NULL,
        date_installed DATE NOT NULL,
        starting_kmr INTEGER NOT NULL,
        current_kmr INTEGER NOT NULL,
        last_checked TIMESTAMP NOT NULL,
        UNIQUE(tipper_id, tire_number)
    )""")
    
    # Create tire_images table for storing images
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tire_images (
        id SERIAL PRIMARY KEY,
        tipper_id VARCHAR(50) NOT NULL,
        tire_number VARCHAR(50) NOT NULL,
        position VARCHAR(50) NOT NULL,
        image_data BYTEA NOT NULL,
        upload_time TIMESTAMP NOT NULL,
        FOREIGN KEY (tipper_id, tire_number) REFERENCES tires (tipper_id, tire_number) ON DELETE CASCADE
    )""")
    
    # Create tippers table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tippers (
        tipper_id VARCHAR(50) PRIMARY KEY,
        registration VARCHAR(100) NOT NULL
    )""")
    
    # Create maintenance table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance (
        id SERIAL PRIMARY KEY,
        tipper_id VARCHAR(50) NOT NULL,
        last_service_mmr INTEGER NOT NULL,
        type_of_service VARCHAR(100),
        due_hours INTEGER NOT NULL,
        current_mmr INTEGER NOT NULL,
        expires_q1 BOOLEAN,
        expires_qii_filter BOOLEAN,
        fust_filter BOOLEAN,
        parts_under_1000hrs BOOLEAN,
        last_updated TIMESTAMP NOT NULL,
        FOREIGN KEY (tipper_id) REFERENCES tippers (tipper_id)
    )""")
    
    # Insert tipper details if table is empty
    cursor.execute("SELECT COUNT(*) FROM tippers")
    if cursor.fetchone()[0] == 0:
        tipper_details = [
            ("TIPPEG-4", "AP39UQ-0095"),
            ("TIPPEG-5", "AP39UQ-0097"),
            ("TIPPEG-6", "AP39UQ-0051"),
            ("TIPPEG-7", "AP39UQ-0052"),
            ("TIPPEG-8", "AP39UQ-0080"),
            ("TIPPEG-9", "AP39UQ-0081"),
            ("TIPPEG-10", "AP39UQ-0026"),
            ("TIPPEG-11", "AP39UQ-0027"),
            ("TIPPEG-12", "AP39UQ-0028")
        ]
        
        for tipper in tipper_details:
            cursor.execute(
                "INSERT INTO tippers (tipper_id, registration) VALUES (%s, %s)",
                tipper
            )
    
    # Insert maintenance data if table is empty
    cursor.execute("SELECT COUNT(*) FROM maintenance")
    if cursor.fetchone()[0] == 0:
        maintenance_data = [
            ("TIPPEG-4", 1000, "", 1000, 2817, True, True, True, True),
            ("TIPPEG-5", 1000, "", 2500, 2322, True, True, True, True),
            ("TIPPEG-6", 1757, "1000hrs Service", 2759, 1025, True, True, True, True),
            ("TIPPEG-7", 0, "", 1000, 1007, True, True, True, True),
            ("TIPPEG-8", 0, "", 1000, 1005, True, True, True, True)
        ]
        
        for data in maintenance_data:
            cursor.execute("""
            INSERT INTO maintenance (
                tipper_id, last_service_mmr, type_of_service, due_hours, 
                current_mmr, expires_q1, expires_qii_filter, fust_filter, 
                parts_under_1000hrs, last_updated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, data + (datetime.now(),))
    
    conn.commit()
    cursor.close()
    conn.close()
    
# Initialize database on app start
initialize_database()

# Function to get all tipper details
def get_tipper_details():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tipper_id, registration FROM tippers ORDER BY tipper_id")
    tippers = cursor.fetchall()
    cursor.close()
    conn.close()
    
    tipper_details = {}
    for tipper in tippers:
        display_name = f"{tipper[0]} - {tipper[1]}"
        tipper_details[tipper[0]] = display_name
    return tipper_details

# Function to get all tires for a specific tipper
def get_tires_for_tipper(tipper_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        tire_number, position, condition_percent, 
        date_installed, starting_kmr, current_kmr, last_checked
    FROM tires
    WHERE tipper_id = %s
    ORDER BY position
    """, (tipper_id,))
    tires = cursor.fetchall()
    
    # Get images for each tire
    tires_with_images = []
    for tire in tires:
        cursor.execute("""
        SELECT image_data FROM tire_images
        WHERE tipper_id = %s AND tire_number = %s
        ORDER BY upload_time DESC
        """, (tipper_id, tire[0]))
        images = [row[0] for row in cursor.fetchall()]
        tires_with_images.append(tire + (images,))
    
    cursor.close()
    conn.close()
    
    return tires_with_images

# Function to save tire images to database
def save_tire_image(tipper_id, tire_number, position, image_file):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO tire_images (
            tipper_id, tire_number, position, image_data, upload_time
        ) VALUES (%s, %s, %s, %s, %s)
        """, (
            tipper_id,
            tire_number,
            position,
            image_file.read(),
            datetime.now()
        ))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving image: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Function to save/update tire data
def save_tire_data(tipper_id, tire_number, position, condition, date_installed, starting_kmr, current_kmr):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if tire exists
        cursor.execute("""
        SELECT 1 FROM tires 
        WHERE tipper_id = %s AND tire_number = %s
        """, (tipper_id, tire_number))
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update existing tire
            cursor.execute("""
            UPDATE tires SET
                position = %s,
                condition_percent = %s,
                date_installed = %s,
                current_kmr = %s,
                last_checked = %s
            WHERE tipper_id = %s AND tire_number = %s
            """, (
                position,
                condition,
                date_installed,
                current_kmr,
                datetime.now(),
                tipper_id,
                tire_number
            ))
        else:
            # Insert new tire
            cursor.execute("""
            INSERT INTO tires (
                tipper_id, tire_number, position,
                condition_percent, date_installed, starting_kmr,
                current_kmr, last_checked
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                tipper_id,
                tire_number,
                position,
                condition,
                date_installed,
                starting_kmr,
                current_kmr,
                datetime.now()
            ))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Database error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Function to get maintenance data
def get_maintenance_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        m.tipper_id, t.registration, m.last_service_mmr, m.type_of_service,
        m.due_hours, m.current_mmr, 
        (m.due_hours - m.current_mmr) as remaining_mmr,
        m.expires_q1, m.expires_qii_filter, m.fust_filter, m.parts_under_1000hrs
    FROM maintenance m
    JOIN tippers t ON m.tipper_id = t.tipper_id
    """)
    
    columns = [desc[0] for desc in cursor.description]
    data = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    df = pd.DataFrame(data, columns=columns)
    df['Display Name'] = df['tipper_id'] + " - " + df['registration']
    return df

# Function to update maintenance record
def update_maintenance_record(tipper_id, service_type, service_date, notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current maintenance data
        cursor.execute("""
        SELECT current_mmr, due_hours FROM maintenance
        WHERE tipper_id = %s
        """, (tipper_id,))
        current_mmr, due_hours = cursor.fetchone()
        
        # Update the maintenance record
        cursor.execute("""
        UPDATE maintenance SET
            last_service_mmr = %s,
            type_of_service = %s,
            current_mmr = %s,
            last_updated = %s
        WHERE tipper_id = %s
        """, (
            current_mmr,
            service_type,
            current_mmr,
            datetime.now(),
            tipper_id
        ))
        
        # Add to service history (would need a separate table)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error updating maintenance record: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Main application
def main():
    st.set_page_config(page_title="Tipper Management System", layout="wide")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox("Choose a module", 
                                  ["Maintenance Dashboard", "Tire Management", "Tipper Information"])
    
    # Get tipper details
    tipper_details = get_tipper_details()
    
    if app_mode == "Maintenance Dashboard":
        st.title("Tipper Maintenance Dashboard")
        st.subheader("May 2025 Service Schedule")
        
        # Load and process data
        df = get_maintenance_data()
        df['Status'] = df.apply(lambda row: 'OVERDUE' if row['remaining_mmr'] < 0 
                               else 'DUE SOON' if row['remaining_mmr'] < 100 
                               else 'OK', axis=1)
        
        # Overview metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tippers", len(df))
        col2.metric("Overdue Services", len(df[df['Status'] == 'OVERDUE']))
        col3.metric("Due Soon", len(df[df['Status'] == 'DUE SOON']))
        
        # Color coding for status
        def color_status(val):
            color = 'red' if val == 'OVERDUE' else 'orange' if val == 'DUE SOON' else 'green'
            return f'background-color: {color}'
        
        # Display main table
        st.dataframe(df.style.applymap(color_status, subset=['Status']))
        
        # Maintenance alerts section
        st.subheader('Maintenance Alerts')
        
        overdue = df[df['Status'] == 'OVERDUE']
        due_soon = df[df['Status'] == 'DUE SOON']
        
        if not overdue.empty:
            st.error('⚠️ Overdue Maintenance')
            st.dataframe(overdue[['Display Name', 'current_mmr', 'due_hours', 'remaining_mmr']])
            
        if not due_soon.empty:
            st.warning('⚠️ Maintenance Due Soon')
            st.dataframe(due_soon[['Display Name', 'current_mmr', 'due_hours', 'remaining_mmr']])
        
        # Filter replacement section
        st.subheader('Filter Replacement Status')
        filter_df = df[['Display Name', 'expires_q1', 'expires_qii_filter', 'fust_filter']]
        st.dataframe(filter_df)
        
        # Service history and scheduling
        st.subheader('Service Scheduling')
        selected_tipper = st.selectbox('Select Tipper', df['Display Name'])
        tipper_id = df[df['Display Name'] == selected_tipper]['tipper_id'].values[0]
        tipper_data = df[df['Display Name'] == selected_tipper].iloc[0]
        
        st.write(f"**Current MMR:** {tipper_data['current_mmr']}")
        st.write(f"**Next Service Due At:** {tipper_data['due_hours']} hours")
        st.write(f"**Remaining Hours Until Service:** {max(0, tipper_data['remaining_mmr'])}")
        
        # Service form
        with st.form("service_form"):
            st.write(f"Log Service for {selected_tipper}")
            service_type = st.selectbox("Service Type", ["1000hrs Service", "2500hrs Service", "Other"])
            service_date = st.date_input("Service Date")
            service_notes = st.text_area("Notes")
            submitted = st.form_submit_button("Submit Service")
            
            if submitted:
                if update_maintenance_record(tipper_id, service_type, service_date, service_notes):
                    st.success(f"Service for {selected_tipper} logged successfully")
                else:
                    st.error("Failed to log service")
    
    elif app_mode == "Tire Management":
        st.title("🚛 Tipper Tire Management System")
        st.markdown("---")
        
        # Select tipper with proper display of all options
        selected_tipper = st.selectbox(
            "Select Tipper", 
            options=list(tipper_details.keys()),
            format_func=lambda x: tipper_details[x],
            index=0
        )
        
        # Define all tire positions
        positions = [
            "Front Left", "Front Right",
            "Middle Left 1", "Middle Right 1",
            "Middle Left 2", "Middle Right 2",
            "Rear Left 1", "Rear Right 1",
            "Rear Left 2", "Rear Right 2"
        ]
        
        # Get existing tires for this tipper
        existing_tires = get_tires_for_tipper(selected_tipper)
        
        # Create a form for all tires
        form = st.form(key="tire_management_form")
        with form:
            st.subheader(f"Tire Details for {tipper_details[selected_tipper]}")
            
            # Create two columns for better layout
            col1, col2 = st.columns(2)
            
            for i, position in enumerate(positions):
                # Alternate between columns
                col = col1 if i % 2 == 0 else col2
                
                with col:
                    st.markdown(f"### {position}")
                    
                    # Find existing data for this position
                    existing_data = next((tire for tire in existing_tires if tire[1] == position), None)
                    
                    # Tire number (fixed based on position)
                    tire_number = f"Tire-{i+1}"
                    st.text_input("Tire Number", value=tire_number, key=f"num_{position}", disabled=True)
                    
                    # Image upload
                    uploaded_file = st.file_uploader(
                        f"Upload {position} Tire Image",
                        type=["jpg", "jpeg", "png"],
                        key=f"img_{position}"
                    )
                    
                    # Display existing images if available
                    if existing_data and existing_data[7]:  # images are at index 7
                        st.write("Existing Images:")
                        img_cols = st.columns(3)
                        for idx, img_data in enumerate(existing_data[7]):
                            try:
                                with img_cols[idx % 3]:
                                    image = Image.open(io.BytesIO(img_data))
                                    st.image(image, caption=f"Image {idx+1}", width=150)
                            except:
                                st.warning(f"Could not load image {idx+1}")
                    
                    # Condition slider
                    condition = st.slider(
                        "Condition (%)",
                        min_value=0, max_value=100,
                        value=existing_data[2] if existing_data else 80,
                        key=f"cond_{position}"
                    )
                    
                    # Date installed
                    date_installed = st.date_input(
                        "Date Installed",
                        value=existing_data[3] if existing_data else datetime.now().date(),
                        key=f"date_{position}"
                    )
                    
                    # KMR inputs
                    kmr_col1, kmr_col2 = st.columns(2)
                    with kmr_col1:
                        starting_kmr = st.number_input(
                            "Starting KMR",
                            min_value=0,
                            value=existing_data[4] if existing_data else 0,
                            key=f"start_{position}"
                        )
                    with kmr_col2:
                        current_kmr = st.number_input(
                            "Current KMR",
                            min_value=starting_kmr,
                            value=existing_data[5] if existing_data else (starting_kmr + 1000),  # Default to starting_kmr + 1000 if new
                            key=f"current_{position}"
                        )
                    
                    st.markdown("---")
            
            # Submit button
            submitted = st.form_submit_button("Save All Tire Data")
        
        if submitted:
            progress_bar = st.progress(0)
            success_count = 0
            
            for i, position in enumerate(positions):
                tire_number = f"Tire-{i+1}"
                
                # Get other form data
                condition = st.session_state.get(f"cond_{position}")
                date_installed = st.session_state.get(f"date_{position}")
                starting_kmr = st.session_state.get(f"start_{position}")
                current_kmr = st.session_state.get(f"current_{position}")
                
                # Save tire data to database
                if save_tire_data(
                    selected_tipper, tire_number, position, 
                    condition, date_installed, 
                    starting_kmr, current_kmr
                ):
                    success_count += 1
                
                # Handle image upload separately
                uploaded_file = st.session_state.get(f"img_{position}")
                if uploaded_file is not None:
                    if save_tire_image(selected_tipper, tire_number, position, uploaded_file):
                        success_count += 0.5  # partial success for image upload
                
                progress_bar.progress((i + 1) / len(positions))
            
            if success_count >= len(positions):
                st.success("All tire data saved successfully!")
            elif success_count > 0:
                st.warning(f"Saved data for {int(success_count)} out of {len(positions)} tires. Some updates may have failed.")
            else:
                st.error("Failed to save any tire data.")
        
        # Display tire dashboard for the selected tipper
        st.subheader("Tire Dashboard")
        tires = get_tires_for_tipper(selected_tipper)
        
        if not tires:
            st.warning(f"No tire data available for {tipper_details[selected_tipper]}")
        else:
            # Convert to DataFrame for visualization
            tires_df = pd.DataFrame(tires, columns=[
                'Tire Number', 'Position', 'Condition (%)',
                'Date Installed', 'Starting KMR', 'Current KMR', 'Last Checked', 'Images'
            ])
            
            # Calculate KMs Run
            tires_df['KMs Run'] = tires_df['Current KMR'] - tires_df['Starting KMR']
            
            # Detailed tire information with color coding
            st.subheader("Detailed Tire Information")
            
            def color_condition(val):
                if val >= 70:
                    color = 'green'
                elif val >= 40:
                    color = 'orange'
                else:
                    color = 'red'
                return f'color: {color}; font-weight: bold'
            
            detailed_df = tires_df[['Position', 'Tire Number', 'Starting KMR', 'Current KMR', 'KMs Run', 'Condition (%)', 'Date Installed']]
            detailed_df = detailed_df.rename(columns={
                'Starting KMR': 'Start KMR',
                'Current KMR': 'Current KMR',
                'KMs Run': 'KMs Run'
            })
            
            st.dataframe(
                detailed_df.style
                .format({
                    'Start KMR': '{:,.0f}',
                    'Current KMR': '{:,.0f}',
                    'KMs Run': '{:,.0f}',
                    'Condition (%)': '{:.0f}%'
                })
                .applymap(color_condition, subset=['Condition (%)'])
                .apply(lambda x: ['background: #ffcccc' if x['Condition (%)'] < 30 else '' for i in x], axis=1),
                use_container_width=True
            )
            
            # Tires needing attention
            critical_tires = tires_df[tires_df['Condition (%)'] < 40]
            if not critical_tires.empty:
                st.warning("⚠️ The following tires need attention:")
                
                def attention_color(row):
                    if row['Condition (%)'] < 20:
                        return ['background-color: #ffcccc'] * len(row)
                    elif row['Condition (%)'] < 30:
                        return ['background-color: #ffe6cc'] * len(row)
                    else:
                        return ['background-color: #fff2cc'] * len(row)
                
                st.dataframe(
                    critical_tires[['Position', 'Tire Number', 'Condition (%)', 'KMs Run']]
                    .style.apply(attention_color, axis=1),
                    use_container_width=True
                )
    
    elif app_mode == "Tipper Information":
        st.title("ℹ️ Tipper Information")
        
        # Display all tippers in a clean table
        conn = get_db_connection()
        tipper_df = pd.read_sql("""
            SELECT 
                t.tipper_id as "Tipper ID", 
                t.registration as Registration,
                COUNT(ty.tire_number) as "Tire Count",
                COALESCE(AVG(ty.condition_percent), 0) as "Avg Condition (%)",
                COALESCE(SUM(ty.current_kmr - ty.starting_kmr), 0) as "Total KMs Run",
                m.current_mmr as "Current MMR",
                m.due_hours as "Next Service Due",
                (m.due_hours - m.current_mmr) as "Remaining Hours"
            FROM tippers t
            LEFT JOIN tires ty ON t.tipper_id = ty.tipper_id
            LEFT JOIN maintenance m ON t.tipper_id = m.tipper_id
            GROUP BY t.tipper_id, t.registration, m.current_mmr, m.due_hours
            ORDER BY t.tipper_id
        """, conn)
        conn.close()
        
        st.dataframe(
            tipper_df.style.format({
                "Avg Condition (%)": "{:.1f}%",
                "Total KMs Run": "{:,.0f} km",
                "Remaining Hours": "{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )

if __name__ == '__main__':
    main()
