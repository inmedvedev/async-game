import time
import asyncio
import curses
import random
import os
from itertools import cycle
from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle
from explosion import explode
from game_scenario import PHRASES, get_garbage_delay_tics

TIC_TIMEOUT = 0.1
SYMBOLS = "+*.:"
STARS_AMOUNT = 100
YEAR = 1957
BORDER_THICKNESS = 1
coroutines = []
obstacles = []
obstacles_in_last_collision = []


def get_frames(dirname):
    frames_list = []
    for filename in os.listdir(os.path.join(os.getcwd(), dirname)):
        with open(
            os.path.join(os.getcwd(), dirname, filename), "r", encoding="utf-8"
        ) as file:
            frames_list.append(file.read())
    return frames_list


async def sleep(tics):
    for _ in range(tics):
        await asyncio.sleep(0)


async def blink(canvas, row, column, offset_tics, symbol="*"):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(offset_tics)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


def get_random_xy(max_x, max_y):
    return random.randint(1, max_x), random.randint(1, max_y)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""
    global obstacles_in_last_collision

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), "*")
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), "O")
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), " ")

    row += rows_speed
    column += columns_speed

    symbol = "-" if columns_speed else "|"

    window_width, window_height = canvas.getmaxyx()
    max_row, max_column = (
        window_width - BORDER_THICKNESS,
        window_height - BORDER_THICKNESS,
    )

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), " ")
        row += rows_speed
        column += columns_speed
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collision.append(obstacle)
                return


async def control_spaceship(canvas, max_x, max_y, frames):
    row_speed = column_speed = 0
    frame_rows, frame_columns = get_frame_size(frames[0])
    row = max_x // 2
    column = max_y // 2

    for frame in cycle(frames):
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        row_speed, column_speed = update_speed(
            row_speed, column_speed, rows_direction, columns_direction
        )
        row += row_speed
        column += column_speed

        column = min(column, max_y - frame_columns)
        row = min(row, max_x - frame_rows)
        column = max(column, BORDER_THICKNESS)
        row = max(row, BORDER_THICKNESS)

        if YEAR >= 2020 and space_pressed:
            coroutines.append(fire(canvas, row, column + frame_columns // 2))

        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                coroutines.append(show_game_over(canvas, max_x // 2, max_y // 2))
                return
        draw_frame(canvas, row, column, frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, frame, negative=True)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    window_width, window_height = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, window_height - 1)

    row = 0

    frame_rows, frame_columns = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, rows_size=frame_rows, columns_size=frame_columns)
    obstacles.append(obstacle)

    try:
        while row < window_width:
            if obstacle in obstacles_in_last_collision:
                await explode(canvas, row, column)
                obstacles_in_last_collision.remove(obstacle)
                return
            draw_frame(canvas, row, column, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, column, garbage_frame, negative=True)
            row += speed
            obstacle.row = row
    finally:
        obstacles.remove(obstacle)


async def fill_orbit_with_garbage(canvas, max_x):
    garbage_frames = get_frames("garbage_frames")

    while True:
        delay_tics = get_garbage_delay_tics(YEAR)
        if not delay_tics:
            await asyncio.sleep(0)
            continue
        await sleep(delay_tics)
        coroutines.append(
            fly_garbage(
                canvas,
                column=random.randint(BORDER_THICKNESS, max_x),
                garbage_frame=random.choice(garbage_frames),
            )
        )


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
    global coroutines
    curses.curs_set(False)
    canvas.nodelay(True)

    spaceship_frames = get_frames("rocket_frames")
    window_width, window_height = canvas.getmaxyx()
    max_x = window_width - BORDER_THICKNESS
    max_y = window_height - BORDER_THICKNESS

    coroutines = [
        blink(
            canvas,
            *get_random_xy(max_x, max_y),
            offset_tics=random.randint(10, 30),
            symbol=random.choice(SYMBOLS),
        )
        for _ in range(STARS_AMOUNT)
    ]
    coroutines.extend(
        [
            control_spaceship(canvas, max_x, max_y, sorted(spaceship_frames * 2)),
            fill_orbit_with_garbage(canvas, max_y),
            count_years(),
            display_phrase(canvas),
        ]
    )
    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        if not coroutines:
            break
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == "__main__":
    curses.update_lines_cols()
    curses.wrapper(draw)
