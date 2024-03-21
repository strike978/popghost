from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from colour import Color
import chardet
from io import StringIO
import numpy as np
import streamlit as st
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
import sqlite3


st.set_page_config(
    page_title="PopGhost",
    page_icon="👻",
    layout="wide"
)

st.title("PopGhost")
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
        # result += str(round(i, 6))+","
        # let's remove rounding for more accurate result?
        result += str(i) + ","

    return result[:-1]


def get_amounts(sample_text):
    texts = sample_text.split('+')
    print("TEXTS:", texts)
    if texts[0] != "":
        amounts = [i.split('@')[1] for i in texts]
        # Removing the percent
        amounts = [float(i[:-1]) for i in amounts]
        return amounts
    else:
        return ""


def get_texts(sample_text):
    texts = sample_text.split('+')
    texts = [i.split('@')[0] for i in texts]
    return texts


def get_encoding(bytes_array):
    return chardet.detect(bytes_array)['encoding']


def generate_cmap(num: int = 50):
    red = Color("red")
    colors = list(red.range_to(Color("green"), num))
    colors_rgb = [i.get_rgb() for i in colors]
    # return ListedColormap(colors_rgb)
    # c = ["darkred","red","lightcoral", "palegreen","green","darkgreen"]
    c = ["mediumblue", "darkviolet", "hotpink", "crimson", "green", "darkgreen"]
    v = [0, .15, .4, 0.6, .9, 1.]
    l = list(zip(v, c))
    return LinearSegmentedColormap.from_list('rg', l, N=256)


@st.cache_resource
def get_db(string_data, ssid: str):
    # data_file = open(filename)
    # string_data = data_file.read()
    dbname = str(hash(string_data)) + ".db"

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

    DB_URL = dbname
    # table_name = "ghost_data"+
    # con = sqlite3.connect(DB_URL, check_same_thread=False)
    con = sqlite3.connect(":memory:", check_same_thread=False)
    cur = con.cursor()
    # rand_int = np.random.randint(12, 314159)
    # table_name = f"ghost_data_{rand_int}"
    table_name = f"ghost_data_{ssid}"
    cur.execute("DROP TABLE IF EXISTS `filedata`")
    cur.execute("DROP TABLE IF EXISTS `ghost_data`")
    cur.execute("CREATE TABLE filedata(population, content)")
    cur.executemany("INSERT INTO filedata VALUES(?, ?)", data_db)
    con.commit()  # Remember to commit the transaction after executing INSERT.
    cur.execute(
        f"CREATE TABLE {table_name}(id integer primary key autoincrement, population, content, amount REAL)")
    return cur, con, table_name

    return cur


uploaded_file = st.file_uploader(
    "Upload G25 Populations File:", type=['csv', 'txt'])
if uploaded_file is not None:
    stringio = StringIO(uploaded_file.getvalue().decode("ISO-8859-1"))
    string_data = stringio.read()

    # Data file

else:
    data_file = open("data.txt")
    string_data = data_file.read()

ssid = get_script_run_ctx().session_id
ssid = ssid.replace('-', '')
# cur, con, tname = get_db(string_data)
cur, con, tname = get_db(string_data, ssid)


def get_sum_amounts():
    added_amounts = cur.execute(f"SELECT amount FROM {tname}").fetchall()
    added_amounts = [float(i[0]) for i in added_amounts]
    return sum(added_amounts)


col_1, col_2, col_3, col_4, col_5 = st.columns([5, 2, 1, 1, 1])

with col_1:

    res = cur.execute("SELECT population FROM filedata")
    choices = [i[0] for i in res.fetchall()]
    selected = st.selectbox('Choose a population:', choices)

with col_2:
    percent = st.number_input(
        'Amount', min_value=0.0, max_value=200.00, value=50.0, label_visibility='hidden')

with col_3:
    st.text('')
    st.text('')
    st.markdown("*%*")

with col_4:
    st.text('')
    st.text('')
    if st.button("Add"):
        res_btn = cur.execute(
            f"SELECT content FROM filedata WHERE population = '{selected}'")
        res_btn_txt = res_btn.fetchone()[0]
        cur.execute("""
            INSERT INTO {0} (population, content, amount) VALUES
            ('{1}', '{2}', {3})
        """.format(tname, selected, res_btn_txt, percent))
        con.commit()

with col_5:
    st.text('')
    st.text('')
    if st.button("Subtract"):
        res_btn = cur.execute(
            f"SELECT content FROM filedata WHERE population = '{selected}'")
        res_btn_txt = res_btn.fetchone()[0]
        cur.execute("""
            INSERT INTO {0} (population, content, amount)  VALUES
            ('{1}', '{2}', {3})
        """.format(tname, selected, res_btn_txt, percent*-1))
        con.commit()


data_mod = cur.execute(f"SELECT id, population, content, amount FROM {tname}")
# p, c, a = data_mod
col_text, col_amount, col_del = st.columns([6, 2, 2])

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


with col_text:
    for i in range(length):
        key = np.random.randint(200, 9000)
        st.text_input("Population",
                      value=samples[i][2],
                      key=key,
                      on_change=cllbk_text,
                      args=[samples[i][0], key],
                      label_visibility='hidden'
                      )


with col_amount:
    for i in range(length):
        key_amount = np.random.randint(40000, 79000)

        st.number_input("Amount",
                        min_value=-300.0,
                        max_value=300.0,
                        value=float(samples[i][3]),
                        key=key_amount,
                        on_change=cllbk_amnt,
                        args=[samples[i][0], key_amount],
                        label_visibility='hidden'
                        )

with col_del:
    for i in range(length):
        st.text('')
        st.text('')
        if i in [1+(i*4) for i in range(length) if i < (length-1)/4]:
            st.text("")
        st.button("Delete",
                  key=np.random.randint(9000, 29000),
                  on_click=cllbk_del,
                  args=[samples[i][0]],
                  )


_, col_sum = st.columns([8, 2])
with col_sum:
    sum_amounts = get_sum_amounts()
    text = f"### {sum_amounts}"
    if sum_amounts != 100.0:
        text += "🚨"
    else:
        text += "✔"

    st.markdown(text)

col_sample, col_sample_btn = st.columns([8, 2])
# st.subheader("Result")
results_zone = st.empty()

with col_sample:
    added_pop = cur.execute(f"SELECT population FROM {tname}").fetchall()
    added_amounts = cur.execute(f"SELECT amount FROM {tname}").fetchall()
    result = ""
    for i in range(len(added_pop)):
        pop = added_pop[i][0]
        amount = float(added_amounts[i][0])
        sign = int(np.sign(amount))
        amount = abs(amount)
        ops = ['-', '', '+']
        if i == 0:
            if sign > 0:
                result += pop + "@" + str(amount) + "%"
            else:
                result += ops[sign+1] + pop + "@" + str(amount) + "%"
        else:
            result += ops[sign+1] + pop + "@" + str(amount) + "%"

    sample_text = st.text_input("Ghost name:", value=result)


with col_sample_btn:
    st.text('')
    st.text('')
    disabled = (get_sum_amounts() != 100.0)
    if st.button("Create Ghost", disabled=disabled):
        added_amounts = cur.execute(f"SELECT amount FROM {tname}").fetchall()
        added_content = cur.execute(f"SELECT content FROM {tname}").fetchall()
        if len(added_amounts) > 0:
            added_amounts = [i[0] for i in added_amounts]
            added_content = [i[0] for i in added_content]
            ghost = create_ghost(added_content, added_amounts)
            ghost_res = sample_text + "," + ghost
            results_zone.code(language="text", body=ghost_res)
