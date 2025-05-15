import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import io
import random

# In-memory data storage
tire_data = {}
maintenance_data = {}
tipper_details = {
    "TIPPEG-4": "TIPPEG-4 - AP39UQ-0095",
    "TIPPEG-5": "TIPPEG-5 - AP39UQ-0097",
    "TIPPEG-6": "TIPPEG-6 - AP39UQ-0051",
    "TIPPEG-7": "TIPPEG-7 - AP39UQ-0052",
    "TIPPEG-8": "TIPPEG-8 - AP39UQ-0080",
    "TIPPEG-9": "TIPPEG-9 - AP39UQ-0081",
    "TIPPEG-10": "TIPPEG-10 - AP39UQ-0026",
    "TIPPEG-11": "TIPPEG-11 - AP39UQ-0027",
    "TIPPEG-12": "TIPPEG-12 - AP39UQ-0028"
}

# Initialize with sample maintenance data
for tipper_id in tipper_details:
    maintenance_data[tipper_id] = {
        "last_service_mmr": random.randint(1000, 2000),
        "type_of_service": random.choice(["1000hrs Service", "2500hrs Service", ""]),
        "due_hours": random.randint(2000, 3000),
        "current_mmr": random.randint(1000, 2500),
        "expires_q1": random.choice([True, False]),
        "expires_qii_filter": random.choice([True, False]),
        "fust_filter": random.choice([True, False]),
        "parts_under_1000hrs": random.choice([True, False]),
        "last_updated": datetime.now()
    }

# Initialize with sample tire data for demonstration
sample_tire_data = []
positions = [
    "Front Left", "Front Right",
    "Middle Left 1", "Middle Right 1",
    "Middle Left 2", "Middle Right 2",
    "Rear Left 1", "Rear Right 1",
    "Rear Left 2", "Rear Right 2"
]

for tipper_id in tipper_details:
    tire_data[tipper_id] = []
    for i, position in enumerate(positions):
        tire_data[tipper_id].append({
            "tire_number": f"Tire-{i+1}",
            "position": position,
            "condition_percent": random.randint(30, 95),
            "date_installed": datetime.now() - timedelta(days=random.randint(30, 365)),
            "starting_kmr": random.randint(1000, 5000),
            "current_kmr": random.randint(5000, 15000),
            "last_checked": datetime.now() - timedelta(days=random.randint(1, 30)),
            "images": []
        })

# Function to get all tires for a specific tipper
def get_tires_for_tipper(tipper_id):
    return tire_data.get(tipper_id, [])

# Function to save tire images (in-memory)
def save_tire_image(tipper_id, tire_number, position, image_file):
    if tipper_id not in tire_data:
        return False
    
    for tire in tire_data[tipper_id]:
        if tire["tire_number"] == tire_number:
            tire["images"].append(image_file.read())
            return True
    return False

# Function to save/update tire data (in-memory)
def save_tire_data(tipper_id, tire_number, position, condition, date_installed, starting_kmr, current_kmr):
    if tipper_id not in tire_data:
        return False
    
    for tire in tire_data[tipper_id]:
        if tire["tire_number"] == tire_number:
            # Update existing tire
            tire.update({
                "position": position,
                "condition_percent": condition,
                "date_installed": date_installed,
                "starting_kmr": starting_kmr,
                "current_kmr": current_kmr,
                "last_checked": datetime.now()
            })
            return True
    
    # If not found, add new tire (though in our demo we pre-populate all positions)
    tire_data[tipper_id].append({
        "tire_number": tire_number,
        "position": position,
        "condition_percent": condition,
        "date_installed": date_installed,
        "starting_kmr": starting_kmr,
        "current_kmr": current_kmr,
        "last_checked": datetime.now(),
        "images": []
    })
    return True

# Function to get maintenance data (in-memory)
def get_maintenance_data():
    data = []
    for tipper_id, details in maintenance_data.items():
        record = details.copy()
        record["tipper_id"] = tipper_id
        record["registration"] = tipper_details[tipper_id].split(" - ")[1]
        record["remaining_mmr"] = record["due_hours"] - record["current_mmr"]
        record["Display Name"] = tipper_details[tipper_id]
        data.append(record)
    
    df = pd.DataFrame(data)
    return df

# Function to update maintenance record (in-memory)
def update_maintenance_record(tipper_id, service_type, service_date, notes):
    if tipper_id not in maintenance_data:
        return False
    
    maintenance_data[tipper_id].update({
        "last_service_mmr": maintenance_data[tipper_id]["current_mmr"],
        "type_of_service": service_type,
        "last_updated": datetime.now()
    })
    return True

# Main application
def main():
    st.set_page_config(page_title="Tipper Management System", layout="wide")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox("Choose a module", 
                                  ["Maintenance Dashboard", "Tire Management", "Tipper Information"])
    
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
        tipper_id = selected_tipper.split(" - ")[0]
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
                    existing_data = next((tire for tire in existing_tires if tire["position"] == position), None)
                    
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
                    if existing_data and existing_data["images"]:
                        st.write("Existing Images:")
                        img_cols = st.columns(3)
                        for idx, img_data in enumerate(existing_data["images"]):
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
                        value=existing_data["condition_percent"] if existing_data else 80,
                        key=f"cond_{position}"
                    )
                    
                    # Date installed
                    date_installed = st.date_input(
                        "Date Installed",
                        value=existing_data["date_installed"] if existing_data else datetime.now().date(),
                        key=f"date_{position}"
                    )
                    
                    # KMR inputs
                    kmr_col1, kmr_col2 = st.columns(2)
                    with kmr_col1:
                        starting_kmr = st.number_input(
                            "Starting KMR",
                            min_value=0,
                            value=existing_data["starting_kmr"] if existing_data else 0,
                            key=f"start_{position}"
                        )
                    with kmr_col2:
                        current_kmr = st.number_input(
                            "Current KMR",
                            min_value=starting_kmr,
                            value=existing_data["current_kmr"] if existing_data else (starting_kmr + 1000),
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
                
                # Save tire data to memory
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
            tires_df = pd.DataFrame(tires)
            
            # Calculate KMs Run
            tires_df['KMs Run'] = tires_df['current_kmr'] - tires_df['starting_kmr']
            
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
            
            detailed_df = tires_df[['position', 'tire_number', 'starting_kmr', 'current_kmr', 'KMs Run', 'condition_percent', 'date_installed']]
            detailed_df = detailed_df.rename(columns={
                'position': 'Position',
                'tire_number': 'Tire Number',
                'starting_kmr': 'Start KMR',
                'current_kmr': 'Current KMR',
                'condition_percent': 'Condition (%)',
                'date_installed': 'Date Installed'
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
            critical_tires = tires_df[tires_df['condition_percent'] < 40]
            if not critical_tires.empty:
                st.warning("⚠️ The following tires need attention:")
                
                def attention_color(row):
                    if row['condition_percent'] < 20:
                        return ['background-color: #ffcccc'] * len(row)
                    elif row['condition_percent'] < 30:
                        return ['background-color: #ffe6cc'] * len(row)
                    else:
                        return ['background-color: #fff2cc'] * len(row)
                
                st.dataframe(
                    critical_tires[['position', 'tire_number', 'condition_percent', 'KMs Run']]
                    .rename(columns={
                        'position': 'Position',
                        'tire_number': 'Tire Number',
                        'condition_percent': 'Condition (%)',
                        'KMs Run': 'KMs Run'
                    })
                    .style.apply(attention_color, axis=1),
                    use_container_width=True
                )
    
    elif app_mode == "Tipper Information":
        st.title("ℹ️ Tipper Information")
        
        # Display all tippers in a clean table
        df = get_maintenance_data()
        df['Avg Condition (%)'] = 0
        df['Tire Count'] = 10  # Since we have 10 positions per tipper
        
        # Calculate average condition for each tipper
        for tipper_id in tipper_details:
            tires = get_tires_for_tipper(tipper_id)
            if tires:
                avg_condition = sum(tire['condition_percent'] for tire in tires) / len(tires)
                df.loc[df['tipper_id'] == tipper_id, 'Avg Condition (%)'] = avg_condition
        
        st.dataframe(
            df[[
                'Display Name', 'Tire Count', 'Avg Condition (%)',
                'current_mmr', 'due_hours', 'remaining_mmr'
            ]].rename(columns={
                'current_mmr': 'Current MMR',
                'due_hours': 'Next Service Due',
                'remaining_mmr': 'Remaining Hours'
            }).style.format({
                "Avg Condition (%)": "{:.1f}%",
                "Remaining Hours": "{:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )

if __name__ == '__main__':
    main()
