# -*- coding: utf-8 -*-
"""Snake game - console, Windows."""
import msvcrt
import os
import random
import time

W, H = 20, 12
SNAKE, FOOD, WALL = "O", "*", "#"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def init():
    grid = [[WALL if x in (0, W-1) or y in (0, H-1) else " " for x in range(W)] for y in range(H)]
    snake = [(W//2, H//2)]
    grid[snake[0][1]][snake[0][0]] = SNAKE
    food = (random.randint(1, W-2), random.randint(1, H-2))
    grid[food[1]][food[0]] = FOOD
    return grid, snake, food, (1, 0)

def draw(grid):
    clear()
    for row in grid:
        print("".join(row))
    print("WASD - move, Q - quit")

def main():
    grid, snake, food, dxdy = init()
    dx, dy = dxdy
    while True:
        draw(grid)
        if msvcrt.kbhit():
            c = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            if c == "q": break
            if c == "w": dx, dy = 0, -1
            elif c == "s": dx, dy = 0, 1
            elif c == "a": dx, dy = -1, 0
            elif c == "d": dx, dy = 1, 0
        nx, ny = snake[0][0] + dx, snake[0][1] + dy
        cell = grid[ny][nx] if 0 <= ny < H and 0 <= nx < W else WALL
        if cell == WALL:
            print("Game Over")
            break
        if cell == FOOD:
            snake.insert(0, (nx, ny))
            grid[ny][nx] = SNAKE
            fx, fy = random.randint(1, W-2), random.randint(1, H-2)
            while grid[fy][fx] != " ":
                fx, fy = random.randint(1, W-2), random.randint(1, H-2)
            food = (fx, fy)
            grid[fy][fx] = FOOD
        else:
            tail = snake.pop()
            grid[tail[1]][tail[0]] = " "
            snake.insert(0, (nx, ny))
            grid[ny][nx] = SNAKE
        time.sleep(0.15)

if __name__ == "__main__":
    main()
