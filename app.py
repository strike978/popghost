import chardet
from io import StringIO
import numpy as np
import streamlit as st
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
import sqlite3
from streamlit_option_menu import option_menu

# TODO Fix encoding

# Set the page configuration with a title, icon, and layout
st.set_page_config(
    page_title="PopGhost",
    page_icon="👻",
    layout="wide"
)

# Create a menu with two options: Ghosts and Convert
menu_selection = option_menu(None, ["👻 Ghosts", "🔄 Convert"],
                             icons=[' ', ' ',],
                             menu_icon="list", default_index=0, orientation="horizontal")


# If the Ghosts option is selected in the menu
if menu_selection == "👻 Ghosts":
    st.caption("Create ghost populations using G25 coordinates")

    # Function to construct an array from a string of text
    def construct_array(array_text: str):
        title, *array = array_text.split(',')
        array = np.fromstring(",".join(array), sep=',')
        return (title, array)

    # Function to create a ghost from a list of arrays and amounts
    def create_ghost(arrays_text: list, amounts: list) -> str:
        result_array = 0
        for i in range(len(arrays_text)):
            title, array = construct_array(arrays_text[i])
            amount = amounts[i]/100
            result_array += amount*array

        result = ""
        for i in result_array:
            result += str(i) + ","

        return result[:-1]

    # Function to get the amounts from a sample text
    def get_amounts(sample_text):
        texts = sample_text.split('+')
        print("TEXTS:", texts)
        if texts[0] != "":
            amounts = [i.split('@')[1] for i in texts]
            amounts = [int(i[:-1]) for i in amounts]
            return amounts
        else:
            return ""

    # Function to get the texts from a sample text
    def get_texts(sample_text):
        texts = sample_text.split('+')
        texts = [i.split('@')[0] for i in texts]
        return texts

    # Function to get the encoding of a bytes array
    def get_encoding(bytes_array):
        return chardet.detect(bytes_array)['encoding']

    # Define a function that will be cached by Streamlit, meaning that
    # the function's output will be stored and reused on subsequent calls.
    # This function takes a string of data and a session ID as input.
    @st.cache_resource
    def get_db(string_data, ssid: str):
        # Split the input string into rows by newline characters
        rows = string_data.split("\n")
        # Initialize an empty dictionary to store the rows
        rows_dict = {}
        # If the last row is empty, remove it
        if rows[-1] == "":
            rows.pop()

        # Initialize an empty list to store the data for the database
        data_db = []
        # For each row in the rows
        for row in rows:
            # Split the row into values by comma characters
            values = row.split(',')
            # The key is the first value in the row
            k = values[0]
            # Add the row to the dictionary with the key
            rows_dict[k] = row
            # Add the key and row to the database data
            data_db.append((k, row))

        # Connect to an SQLite database in memory
        con = sqlite3.connect(":memory:", check_same_thread=False)
        # Create a cursor object
        cur = con.cursor()
        # Define the table name using the session ID
        table_name = f"ghost_data_{ssid}"
        # Drop the filedata table if it exists
        cur.execute("DROP TABLE IF EXISTS `filedata`")
        # Drop the ghost_data table if it exists
        cur.execute("DROP TABLE IF EXISTS `ghost_data`")
        # Create a new filedata table with population and content columns
        cur.execute("CREATE TABLE filedata(population, content)")
        # Insert the database data into the filedata table
        cur.executemany("INSERT INTO filedata VALUES(?, ?)", data_db)
        # Commit the transaction
        con.commit()
        # Create a new table with the defined table name, with id, population, content, and amount columns
        # The id column is an integer primary key that autoincrements
        cur.execute(
            f"CREATE TABLE {table_name}(id integer primary key autoincrement, population, content, amount REAL)")
        # Return the cursor, connection, and table name
        return cur, con, table_name

    # Create a file uploader widget in the Streamlit app. The widget accepts .csv and .txt files.
    uploaded_file = st.file_uploader(
        "Upload Global 25 PCA spreadsheet", type=['csv', 'txt'])

    # If a file has been uploaded
    if uploaded_file is not None:
        # Decode the uploaded file's content to a string using ISO-8859-15 encoding and read it into a StringIO object
        stringio = StringIO(uploaded_file.getvalue().decode("ISO-8859-15"))
        # Read the entire content of the StringIO object into a string
        string_data = stringio.read()

    # If no file has been uploaded
    else:
        # Open the file "data.txt" in read mode with UTF-8 encoding
        with open("data.txt", 'r', encoding='utf-8') as data_file:
            # Read the entire content of the file into a string
            string_data = data_file.read()

    # Get the current Streamlit session ID
    ssid = get_script_run_ctx().session_id
    # Remove any hyphens from the session ID
    ssid = ssid.replace('-', '')
    # Call the get_db function with the string data and session ID, and unpack its return values into cur, con, and tname
    cur, con, tname = get_db(string_data, ssid)

    # Define a function that calculates the sum of all amounts in the database table
    def get_sum_amounts():
        # Execute a SQL query that selects all amounts from the table
        added_amounts = cur.execute(f"SELECT amount FROM {tname}").fetchall()
        # Convert the fetched amounts to integers
        added_amounts = [int(i[0]) for i in added_amounts]
        # Return the sum of the amounts
        return sum(added_amounts)

    # Create three columns in the Streamlit app with specified widths
    col1, col2, col3 = st.columns([7, 1, 5])  # Adjust the widths as needed

    # In the first column
    with col1:
        # Execute a SQL query that selects all populations from the filedata table
        res = cur.execute("SELECT population FROM filedata")
        # Fetch all rows from the query result and extract the population from each row
        choices = [i[0] for i in res.fetchall()]
        # Create a select box in the Streamlit app that allows the user to choose a population
        selected = st.selectbox('Choose a population', choices)

    # In the second column
    with col2:
        # Create a number input in the Streamlit app that allows the user to input an amount
        percent = st.number_input(
            'Amount', min_value=0, max_value=200, value=50, step=1, label_visibility='hidden')

    # In the third column
    with col3:
        st.write('')
        st.write('')
        # Create two buttons in the Streamlit app that allow the user to add or subtract the selected population
        add_btn, subtract_btn = st.columns(2)
        # If the Add button is clicked
        if add_btn.button("Add"):
            # Execute a SQL query that selects the content of the selected population from the filedata table
            res_btn = cur.execute(
                f"SELECT content FROM filedata WHERE population = '{selected}'")
            # Fetch the first row from the query result and extract the content
            res_btn_txt = res_btn.fetchone()[0]
            # Execute a SQL query that inserts the selected population, its content, and the input amount into the table
            cur.execute("""
                INSERT INTO {0} (population, content, amount) VALUES
                ('{1}', '{2}', {3})
            """.format(tname, selected, res_btn_txt, percent))
            # Commit the transaction
            con.commit()

        # If the Subtract button is clicked
        if subtract_btn.button("Subtract"):
            # Execute a SQL query that selects the content of the selected population from the filedata table
            res_btn = cur.execute(
                f"SELECT content FROM filedata WHERE population = '{selected}'")
            # Fetch the first row from the query result and extract the content
            res_btn_txt = res_btn.fetchone()[0]
            # Execute a SQL query that inserts the selected population, its content, and the negative input amount into the table
            cur.execute("""
                INSERT INTO {0} (population, content, amount)  VALUES
                ('{1}', '{2}', {3})
            """.format(tname, selected, res_btn_txt, percent * -1))
            # Commit the transaction
            con.commit()

    # Execute a SQL query that selects all rows from the table
    data_mod = cur.execute(
        f"SELECT id, population, content, amount FROM {tname}")

    # Fetch all rows from the query result
    samples = data_mod.fetchall()
    # Get the number of rows
    length = len(samples)

    # Define a callback function to delete a row from the database table
    def cllbk_del(id_):
        # Create a SQL query to delete the row with the specified ID
        query = f"DELETE FROM {tname} WHERE id='{id_}'"
        # Execute the query
        cur.execute(query)
        # Commit the transaction
        con.commit()

    # Define a callback function to update the content of a row in the database table
    def cllbk_text(id_, key_content):
        # Get the new content from the session state
        new_content = st.session_state[key_content]
        # Create a SQL query to update the content of the row with the specified ID
        query = f"UPDATE {tname} SET content='{new_content}' WHERE id='{id_}'"
        # Execute the query
        cur.execute(query)
        # Commit the transaction
        con.commit()

    # Define a callback function to update the amount of a row in the database table
    def cllbk_amnt(id_, key_amount):
        # Get the new amount from the session state
        new_amount = st.session_state[key_amount]
        # Create a SQL query to update the amount of the row with the specified ID
        query = f"UPDATE {tname} SET amount='{new_amount}' WHERE id='{id_}'"
        # Execute the query
        cur.execute(query)
        # Commit the transaction
        con.commit()

    # For each row in the database table
    for i in range(length):
        # Create three columns in the Streamlit app
        col4, col5, col6 = st.columns([7, 1, 5])
        # In the first column
        with col4:
            # Create a text input that allows the user to update the population of the row
            key = np.random.randint(200, 9000)
            st.text_input("Population",
                          value=samples[i][2],
                          key=key,
                          on_change=cllbk_text,
                          args=[samples[i][0], key],
                          label_visibility='hidden'
                          )
        # In the second column
        with col5:
            # Create a number input that allows the user to update the amount of the row
            key_amount = np.random.randint(40000, 79000)
            st.number_input("Amount",
                            min_value=-300,
                            max_value=300,
                            step=1,
                            value=int(samples[i][3]),
                            key=key_amount,
                            on_change=cllbk_amnt,
                            args=[samples[i][0], key_amount],
                            label_visibility='hidden'
                            )
        # In the third column
        with col6:
            # Create a button that allows the user to delete the row
            st.text('')
            st.text('')
            st.button("🗑️",
                      key=np.random.randint(9000, 29000),
                      on_click=cllbk_del,
                      args=[samples[i][0]],
                      help="Delete",
                      )

    # Create a column in the Streamlit app to display the sum of the amounts
    _, col_sum = st.columns([8, 2])
    with col_sum:
        # Calculate the sum of the amounts
        sum_amounts = get_sum_amounts()
        # Create a string to display the sum
        text = f"### {sum_amounts}"
        # If the sum is not 100, add a warning symbol to the string
        if sum_amounts != 100:
            text += " ⛔"
        # If the sum is 100, add a checkmark symbol to the string
        else:
            text += " ✅"
        # Display the string in the Streamlit app
        st.markdown(text)

    # Create two columns in the Streamlit app to input a ghost name and create a ghost
    col_sample, col_sample_btn = st.columns([8, 2])
    # Create an empty container to display the results
    results_zone = st.empty()

    # In the first column
    with col_sample:
        # Create a text input to input a ghost name
        sample_text = st.text_input("Ghost name")

    # In the second column
    with col_sample_btn:
        # Create a button to create a ghost
        st.text('')
        st.text('')
        # Disable the button if the sum of the amounts is not 100 or the ghost name is empty
        disabled = (get_sum_amounts() != 100) or (sample_text.strip() == "")
        # If the button is clicked
        if st.button("Create Ghost", disabled=disabled):
            # Execute SQL queries to select all amounts and content from the table
            added_amounts = cur.execute(
                f"SELECT amount FROM {tname}").fetchall()
            added_content = cur.execute(
                f"SELECT content FROM {tname}").fetchall()
            # If there are any rows in the table
            if len(added_amounts) > 0:
                # Convert the fetched amounts and content to lists
                added_amounts = [i[0] for i in added_amounts]
                added_content = [i[0] for i in added_content]
                # Create a ghost with the added content and amounts
                ghost = create_ghost(added_content, added_amounts)
                # Create a string to display the ghost name and the ghost
                ghost_res = sample_text + "," + ghost
                # Display the string in the results container
                results_zone.code(language="text", body=ghost_res)

# This section of the code is executed when the user selects "🔄 Convert" from the menu
elif menu_selection == "🔄 Convert":
    # Define a list of eigenvalues
    EIGENVALUES = [129.557, 103.13, 14.222, 10.433, 9.471, 7.778, 5.523, 5.325, 4.183, 3.321, 2.637,
                   2.246, 2.21, 1.894, 1.842, 1.758, 1.7, 1.605, 1.58, 1.564, 1.557, 1.529, 1.519, 1.452, 1.434]

    # Define a function to parse the scaled coordinates input by the user
    def parse_scaled_coordinates(scaled_coordinates_input):
        # Split the input into lines
        lines = scaled_coordinates_input.split('\n')
        # Initialize an empty dictionary to store the parsed coordinates
        scaled_coordinates_dict = {}
        # For each line in the input
        for line in lines:
            # Split the line into parts by comma
            parts = line.split(',')
            # If the line contains more than one part
            if len(parts) > 1:  # Skip lines with only name and no coordinates
                # The first part is the name
                name = parts[0].strip()  # Remove leading/trailing whitespace
                # The remaining parts are the coordinates
                # Remove leading/trailing whitespace from each coordinate and convert it to a float
                coordinates = [float(x.strip()) for x in parts[1:]]
                # Add the name and coordinates to the dictionary
                scaled_coordinates_dict[name] = coordinates
        # Return the dictionary of parsed coordinates
        return scaled_coordinates_dict

    # Define a function to convert scaled coordinates to unscaled coordinates
    def convert_scaled_to_unscaled(scaled_coordinates_dict, eigenvalues):
        # Initialize an empty dictionary to store the unscaled coordinates
        unscaled_coordinates_dict = {}
        # For each name and coordinates in the dictionary of scaled coordinates
        for name, coordinates in scaled_coordinates_dict.items():
            # Divide the coordinates by the square root of the eigenvalues to get the unscaled coordinates
            unscaled_coordinates = np.divide(coordinates, np.sqrt(eigenvalues))
            # Add the name and unscaled coordinates to the dictionary
            unscaled_coordinates_dict[name] = unscaled_coordinates
        # Return the dictionary of unscaled coordinates
        return unscaled_coordinates_dict

    # Display a caption in the Streamlit app
    st.caption(
        "Convert G25 scaled coordinates to unscaled coordinates")

    # Create a text area in the Streamlit app for the user to enter the scaled coordinates
    scaled_coordinates_input = st.text_area(
        "Enter scaled coordinates (name, followed by comma-separated values)")

    # When the user clicks the "Convert Coordinates" button
    if st.button("Convert Coordinates"):
        # Parse the scaled coordinates input by the user
        scaled_coordinates_dict = parse_scaled_coordinates(
            scaled_coordinates_input)
        # Convert the parsed scaled coordinates to unscaled coordinates
        unscaled_coordinates_dict = convert_scaled_to_unscaled(
            scaled_coordinates_dict, EIGENVALUES)

        # Initialize an empty string to store the unscaled result
        unscaled_result = ""
        # For each name and unscaled coordinates in the dictionary of unscaled coordinates
        for name, unscaled_coordinates in unscaled_coordinates_dict.items():
            # Round each unscaled coordinate to 6 decimal places
            rounded_coordinates = [round(coord, 6)
                                   for coord in unscaled_coordinates]
            # Add the name and rounded unscaled coordinates to the unscaled result string
            unscaled_result += name + "," + \
                ",".join(map(str, rounded_coordinates)) + "\n"

        # Display the unscaled result in a text area in the Streamlit app
        st.text_area("Unscaled coordinates", value=unscaled_result)
