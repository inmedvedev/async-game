import time
import asyncio
import curses
import random
import os
import uuid
from itertools import cycle
from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle
from explosion import explode
from game_scenario import PHRASES, get_garbage_delay_tics

TIC_TIMEOUT = 0.1
SYMBOLS = "+*.:"
SPACESHIP_FRAME = ""
STARS_AMOUNT = 100
COROUTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISION = []
YEAR = 1957


def get_frames(dirname):
    frames_list = []
    for filename in os.listdir(os.path.join(os.getcwd(), dirname)):
        with open(
            os.path.join(os.getcwd(), dirname, filename), "r", encoding="utf-8"
        ) as file:
            frames_list.append(file.read())
    return frames_list


async def sleep(start_tics_range=1, final_tics_range=None):
    if final_tics_range is not None:
        for _ in range(random.randint(start_tics_range, final_tics_range)):
            await asyncio.sleep(0)
    for _ in range(start_tics_range):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol="*"):

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(10, 30)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


def get_random_xy(max_x, max_y):
    return random.randint(1, max_x - 2), random.randint(1, max_y - 2)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""
    global OBSTACLES_IN_LAST_COLLISION

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), "*")
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), "O")
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), " ")

    row += rows_speed
    column += columns_speed

    symbol = "-" if columns_speed else "|"

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), " ")
        row += rows_speed
        column += columns_speed
        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column):
                OBSTACLES_IN_LAST_COLLISION.append(obstacle)
                return


async def animate_spaceship(frames):
    global SPACESHIP_FRAME

    for frame in cycle(frames):
        SPACESHIP_FRAME = frame
        await sleep(2)


async def control_spaceship(canvas, row, column):
    last_frame = ""
    row_speed = column_speed = 0
    frame_columns = None

    while True:
        if last_frame != SPACESHIP_FRAME:
            draw_frame(canvas, row, column, last_frame, negative=True)
        draw_frame(canvas, row, column, SPACESHIP_FRAME, negative=True)
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        row_speed, column_speed = update_speed(
            row_speed, column_speed, rows_direction, columns_direction
        )
        row += row_speed
        column += column_speed

        max_x, max_y = canvas.getmaxyx()

        if bool(SPACESHIP_FRAME):
            frame_rows, frame_columns = get_frame_size(SPACESHIP_FRAME)
            if row > max_x - frame_rows - 1:
                row = max_x - frame_rows - 1
            if column > max_y - frame_columns - 1:
                column = max_y - frame_columns - 1
            column = max(column, 1)
            row = max(row, 1)

        if YEAR >= 2020 and space_pressed:
            COROUTINES.append(fire(canvas, row, column + frame_columns // 2))

        for obstacle in OBSTACLES:
            if obstacle.has_collision(row, column):
                COROUTINES.append(show_game_over(canvas, max_x // 2, max_y // 2))
                return

        draw_frame(canvas, row, column, SPACESHIP_FRAME)
        last_frame = SPACESHIP_FRAME
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    frame_rows, frame_columns = get_frame_size(garbage_frame)
    uid = uuid.uuid4()
    obstacle = Obstacle(
        row, column, rows_size=frame_rows, columns_size=frame_columns, uid=uid
    )
    OBSTACLES.append(obstacle)

    try:
        while row < rows_number:
            if obstacle in OBSTACLES_IN_LAST_COLLISION:
                await explode(canvas, row, column)
                OBSTACLES_IN_LAST_COLLISION.remove(obstacle)
                return
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            obstacle.row = row
    finally:
        OBSTACLES.remove(obstacle)


async def fill_orbit_with_garbage(canvas, max_x):
    garbage_frames = get_frames("garbage_frames")
    while True:
        delay_tics = get_garbage_delay_tics(YEAR)
        if delay_tics:
            await sleep(delay_tics)
            COROUTINES.append(
                fly_garbage(
                    canvas,
                    column=random.randint(1, max_x),
                    garbage_frame=random.choice(garbage_frames),
                )
            )
        await asyncio.sleep(0)


async def show_game_over(canvas, row, column):
    with open("game_over.txt", "r") as game_over_frame:
        frame = game_over_frame.read()
    frame_rows, frame_columns = get_frame_size(frame)
    while True:
        draw_frame(canvas, row - frame_rows // 2, column - frame_columns // 2, frame)
        await asyncio.sleep(0)


async def count_years():
    global YEAR
    while True:
        await sleep(15)
        YEAR += 1


async def display_phrase(canvas):
    while True:
        draw_frame(canvas, 0, 0, f"Year - {YEAR}")
        await asyncio.sleep(0)
        if YEAR in PHRASES.keys():
            year, phrase = YEAR, PHRASES[YEAR]
            draw_frame(canvas, 0, 0, f"Year - {year}: {phrase}")
            await sleep(15)
            draw_frame(canvas, 0, 0, f"Year - {year}: {phrase}", negative=True)


def draw(canvas):
    global COROUTINES
    curses.curs_set(False)
    canvas.nodelay(True)

    spaceship_frames = get_frames("rocket_frames")
    max_x, max_y = canvas.getmaxyx()

    COROUTINES = [
        blink(canvas, *get_random_xy(max_x, max_y), random.choice(SYMBOLS))
        for _ in range(STARS_AMOUNT)
    ]
    COROUTINES.extend(
        [
            control_spaceship(canvas, max_x // 2, max_y // 2),
            animate_spaceship(spaceship_frames),
            fill_orbit_with_garbage(canvas, max_y),
            count_years(),
            display_phrase(canvas),
        ]
    )
    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)
        if not COROUTINES:
            break
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == "__main__":
    curses.update_lines_cols()
    curses.wrapper(draw)
