import time
import asyncio
import curses
import random
import os
from itertools import cycle
from curses_tools import draw_frame, read_controls, get_frame_size

TIC_TIMEOUT = 0.1
SYMBOLS = '+*.:'
SPACESHIP_FRAME = ''
STARS_AMOUNT = 100


def get_frames():
    frames_list = []
    for filename in os.listdir(os.path.join(os.getcwd(), 'frames')):
        with open(os.path.join(os.getcwd(), 'frames', filename), 'r', encoding='utf-8') as file:
            frames_list.append(file.read())
    return frames_list


async def blink(canvas, row, column, symbol='*'):

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(random.randint(10, 30)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

def get_random_xy(max_x, max_y):
    return random.randint(1, max_x-2), random.randint(1, max_y-2)


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def animate_spaceship(frames):
    global SPACESHIP_FRAME

    for frame in cycle(frames):
        SPACESHIP_FRAME = frame
        for _ in range(2):
            await asyncio.sleep(0)


async def control_spaceship(canvas, row, column):
    last_frame = ''

    while True:
        if last_frame != SPACESHIP_FRAME:
            draw_frame(canvas, row, column, last_frame, negative=True)
        draw_frame(canvas, row, column, SPACESHIP_FRAME, negative=True)
        rows_direction, columns_direction, space_pressed = read_controls(canvas)
        row += rows_direction
        column += columns_direction

        max_x, max_y = canvas.getmaxyx()
        if bool(SPACESHIP_FRAME):
            frame_rows, frame_columns = get_frame_size(SPACESHIP_FRAME)
            if row > max_x - frame_rows - 1:
                row = max_x - frame_rows - 1
            if column > max_y - frame_columns - 1:
                column = max_y - frame_columns - 1
            column = max(column, 1)
            row = max(row, 1)

        draw_frame(canvas, row, column, SPACESHIP_FRAME)
        last_frame = SPACESHIP_FRAME
        await asyncio.sleep(0)


def draw(canvas):
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    frames = get_frames()

    max_x, max_y = canvas.getmaxyx()
    coroutines = [
        blink(canvas, *get_random_xy(max_x, max_y), random.choice(SYMBOLS))
        for _ in range(STARS_AMOUNT)
    ]
    coroutines.append(control_spaceship(canvas, max_x // 2, max_y // 2))
    coroutines.append(animate_spaceship(frames))
    coroutines.append(fire(canvas, max_x - 2, max_y / 2))
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


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
