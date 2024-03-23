import chardet
from io import StringIO
import numpy as np
import streamlit as st
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
import sqlite3
from streamlit_option_menu import option_menu

# TODO Fix encoding

st.set_page_config(
    page_title="PopGhost",
    page_icon="👻",
    layout="wide"
)

menu_selection = option_menu(None, ["👻 Ghosts", "🔄 Convert"],
                             icons=[' ', ' ',],
                             menu_icon="list", default_index=0, orientation="horizontal")


# Ghost section
if menu_selection == "👻 Ghosts":
    st.caption("Create ghost populations using G25 coordinates")

    def construct_array(array_text: str):
        """
        Get the title and create an array from a string of csv.
        >>> array_text = "Yamnaya_RUS_Samara, 0.1255849,0.089028,0.0426986"
        >>> construct_array(array_text)
        ('Yamnaya_RUS_Samara', array([0.1255849, 0.089028 , 0.0426986]))

        Parameters
        ----------
        array_text: str, the array containing data.
        Returns
        -------
        A tuple (title, array):
        title: str, the title of the array
        array: np.array of floats
        """
        title, *array = array_text.split(',')
        array = np.fromstring(",".join(array), sep=',')
        return (title, array)

    def create_ghost(arrays_text: list, amounts: list) -> str:
        """
        Calculate the ghost of the arrays

        Parameters
        ----------
        arrays_text: list of all the input arrays
        amounts_text: list of the weights

        Returns
        -------
        result: str, the ghost of the arrays
        """
        result_array = 0
        for i in range(len(arrays_text)):
            title, array = construct_array(arrays_text[i])
            amount = amounts[i]/100
            result_array += amount*array

        result = ""
        for i in result_array:
            result += str(i) + ","

        return result[:-1]

    def get_amounts(sample_text):
        texts = sample_text.split('+')
        print("TEXTS:", texts)
        if texts[0] != "":
            amounts = [i.split('@')[1] for i in texts]
            amounts = [int(i[:-1]) for i in amounts]
            return amounts
        else:
            return ""

    def get_texts(sample_text):
        texts = sample_text.split('+')
        texts = [i.split('@')[0] for i in texts]
        return texts

    def get_encoding(bytes_array):
        return chardet.detect(bytes_array)['encoding']

    @st.cache_resource
    def get_db(string_data, ssid: str):
        rows = string_data.split("\n")
        rows_dict = {}
        if rows[-1] == "":
            rows.pop()

        data_db = []
        for row in rows:
            values = row.split(',')
            k = values[0]
            rows_dict[k] = row
            data_db.append((k, row))

        con = sqlite3.connect(":memory:", check_same_thread=False)
        cur = con.cursor()
        table_name = f"ghost_data_{ssid}"
        cur.execute("DROP TABLE IF EXISTS `filedata`")
        cur.execute("DROP TABLE IF EXISTS `ghost_data`")
        cur.execute("CREATE TABLE filedata(population, content)")
        cur.executemany("INSERT INTO filedata VALUES(?, ?)", data_db)
        # Remember to commit the transaction after executing INSERT.
        con.commit()
        cur.execute(
            f"CREATE TABLE {table_name}(id integer primary key autoincrement, population, content, amount REAL)")
        return cur, con, table_name

    uploaded_file = st.file_uploader(
        "Upload Global 25 PCA spreadsheet", type=['csv', 'txt'])
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("ISO-8859-15"))
        string_data = stringio.read()

    else:
        # data_file = open("data.txt")
        # string_data = data_file.read()
        with open("data.txt", 'r', encoding='utf-8') as data_file:
            string_data = data_file.read()

    ssid = get_script_run_ctx().session_id
    ssid = ssid.replace('-', '')
    cur, con, tname = get_db(string_data, ssid)

    def get_sum_amounts():
        added_amounts = cur.execute(f"SELECT amount FROM {tname}").fetchall()
        added_amounts = [int(i[0]) for i in added_amounts]
        return sum(added_amounts)

    col1, col2, col3 = st.columns([7, 1, 5])  # Adjust the widths as needed

    with col1:
        res = cur.execute("SELECT population FROM filedata")
        choices = [i[0] for i in res.fetchall()]
        selected = st.selectbox('Choose a population', choices)

    with col2:
        percent = st.number_input(
            'Amount', min_value=0, max_value=200, value=50, step=1, label_visibility='hidden')

    with col3:
        st.write('')
        st.write('')
        add_btn, subtract_btn = st.columns([2, 15])
        if add_btn.button("Add"):
            res_btn = cur.execute(
                f"SELECT content FROM filedata WHERE population = '{selected}'")
            res_btn_txt = res_btn.fetchone()[0]
            cur.execute("""
                INSERT INTO {0} (population, content, amount) VALUES
                ('{1}', '{2}', {3})
            """.format(tname, selected, res_btn_txt, percent))
            con.commit()

        if subtract_btn.button("Subtract"):
            res_btn = cur.execute(
                f"SELECT content FROM filedata WHERE population = '{selected}'")
            res_btn_txt = res_btn.fetchone()[0]
            cur.execute("""
                INSERT INTO {0} (population, content, amount)  VALUES
                ('{1}', '{2}', {3})
            """.format(tname, selected, res_btn_txt, percent * -1))
            con.commit()

    data_mod = cur.execute(
        f"SELECT id, population, content, amount FROM {tname}")

    samples = data_mod.fetchall()
    length = len(samples)

    def cllbk_del(id_):
        query = f"DELETE FROM {tname} WHERE id='{id_}'"
        cur.execute(query)
        con.commit()

    def cllbk_text(id_, key_content):
        new_content = st.session_state[key_content]
        query = f"UPDATE {tname} SET content='{new_content}' WHERE id='{id_}'"
        cur.execute(query)
        con.commit()

    def cllbk_amnt(id_, key_amount):
        new_amount = st.session_state[key_amount]
        query = f"UPDATE {tname} SET amount='{new_amount}' WHERE id='{id_}'"
        cur.execute(query)
        con.commit()

    for i in range(length):
        col4, col5, col6 = st.columns([7, 1, 5])
        with col4:
            key = np.random.randint(200, 9000)
            st.text_input("Population",
                          value=samples[i][2],
                          key=key,
                          on_change=cllbk_text,
                          args=[samples[i][0], key],
                          label_visibility='hidden'
                          )
        with col5:
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
        with col6:
            st.text('')
            st.text('')
            st.button("🗑️",
                      key=np.random.randint(9000, 29000),
                      on_click=cllbk_del,
                      args=[samples[i][0]],
                      help="Delete",
                      )

    _, col_sum = st.columns([8, 2])
    with col_sum:
        sum_amounts = get_sum_amounts()
        text = f"### {sum_amounts}"
        if sum_amounts != 100:
            text += "⛔"
        else:
            text += "✅"

        st.markdown(text)

    col_sample, col_sample_btn = st.columns([8, 2])
    results_zone = st.empty()

    with col_sample:
        sample_text = st.text_input("Ghost name")

    with col_sample_btn:
        st.text('')
        st.text('')
        disabled = (get_sum_amounts() != 100) or (sample_text.strip() == "")
        if st.button("Create Ghost", disabled=disabled):
            added_amounts = cur.execute(
                f"SELECT amount FROM {tname}").fetchall()
            added_content = cur.execute(
                f"SELECT content FROM {tname}").fetchall()
            if len(added_amounts) > 0:
                added_amounts = [i[0] for i in added_amounts]
                added_content = [i[0] for i in added_content]
                ghost = create_ghost(added_content, added_amounts)
                ghost_res = sample_text + "," + ghost
                results_zone.code(language="text", body=ghost_res)

# Convert section
elif menu_selection == "🔄 Convert":
    EIGENVALUES = [129.557, 103.13, 14.222, 10.433, 9.471, 7.778, 5.523, 5.325, 4.183, 3.321, 2.637,
                   2.246, 2.21, 1.894, 1.842, 1.758, 1.7, 1.605, 1.58, 1.564, 1.557, 1.529, 1.519, 1.452, 1.434]

    def parse_scaled_coordinates(scaled_coordinates_input):
        lines = scaled_coordinates_input.split('\n')
        scaled_coordinates_dict = {}
        for line in lines:
            parts = line.split(',')
            if len(parts) > 1:  # Skip lines with only name and no coordinates
                name = parts[0].strip()  # Remove leading/trailing whitespace
                # Remove leading/trailing whitespace from each coordinate
                coordinates = [float(x.strip()) for x in parts[1:]]
                scaled_coordinates_dict[name] = coordinates
        return scaled_coordinates_dict

    def convert_scaled_to_unscaled(scaled_coordinates_dict, eigenvalues):
        unscaled_coordinates_dict = {}
        for name, coordinates in scaled_coordinates_dict.items():
            unscaled_coordinates = np.divide(coordinates, np.sqrt(eigenvalues))
            unscaled_coordinates_dict[name] = unscaled_coordinates
        return unscaled_coordinates_dict

    st.caption(
        "Convert G25 scaled coordinates to unscaled coordinates")

    scaled_coordinates_input = st.text_area(
        "Enter scaled coordinates (name, followed by comma-separated values)")

    if st.button("Convert Coordinates"):
        scaled_coordinates_dict = parse_scaled_coordinates(
            scaled_coordinates_input)
        unscaled_coordinates_dict = convert_scaled_to_unscaled(
            scaled_coordinates_dict, EIGENVALUES)

        unscaled_result = ""
        for name, unscaled_coordinates in unscaled_coordinates_dict.items():
            rounded_coordinates = [round(coord, 6)
                                   for coord in unscaled_coordinates]
            unscaled_result += name + "," + \
                ",".join(map(str, rounded_coordinates)) + "\n"

        st.text_area("Unscaled coordinates", value=unscaled_result)
