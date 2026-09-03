"""Xiaomi S20 joystick controller.

Usage:
    python controller.py --ip 192.168.1.42 --token YOUR_32_CHAR_TOKEN
"""

import argparse
import getpass
import os
import time
import traceback

import pygame
from miio import Device

DEADZONE = 0.1
COMMAND_INTERVAL = 0.1
DEVICE_ID = "1069182766"
SIID_DIRECTION = 7
PIID_DIRECTION = 16
FORWARD = 1
LEFT = 2
RIGHT = 3
BACKWARD = 4
STOP = 5
EXIT = 10


def apply_deadzone(value: float) -> float:
    return 0.0 if abs(value) < DEADZONE else value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Xiaomi S20'i gamepad ile kontrol et")
    parser.add_argument("--ip", default=os.getenv("VACUUM_IP"), help="Robotun yerel IP adresi")
    parser.add_argument("--token", default=os.getenv("VACUUM_TOKEN"), help="32 karakterlik cihaz tokeni")
    parser.add_argument("--joystick", type=int, default=0, help="Kullanılacak joystick sırası")
    return parser.parse_args()


def request_device_info(args: argparse.Namespace) -> argparse.Namespace:
    if not args.ip:
        args.ip = input("Robotun IP adresi (ör. 192.168.1.42): ").strip()
    if not args.token:
        args.token = getpass.getpass("32 karakterlik token: ").strip()
    return args


def send_direction(vacuum: Device, direction: int) -> None:
    vacuum.send(
        "set_properties",
        [{"did": DEVICE_ID, "siid": SIID_DIRECTION, "piid": PIID_DIRECTION, "value": direction}],
    )


def main() -> None:
    args = request_device_info(parse_args())
    if not args.ip or not args.token:
        raise SystemExit("IP ve token gerekli: --ip ... --token ...")
    if len(args.token) != 32:
        raise SystemExit("Token tam olarak 32 karakter olmalı")

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() <= args.joystick:
        pygame.quit()
        raise SystemExit("Seçilen joystick bulunamadı")

    joystick = pygame.joystick.Joystick(args.joystick)
    vacuum = Device(args.ip, args.token)

    print(f"Joystick bağlandı: {joystick.get_name()}")
    print(f"{args.ip} adresindeki süpürgeye bağlanılıyor...")
    print("S20 joystick kontrolü başladı. Çıkmak için CTRL+C")

    try:
        while True:
            pygame.event.pump()
            axis_y = apply_deadzone(-joystick.get_axis(1))
            axis_x = apply_deadzone(joystick.get_axis(0))
            if axis_y > DEADZONE:
                direction = FORWARD
            elif axis_y < -DEADZONE:
                direction = BACKWARD
            elif axis_x > DEADZONE:
                direction = RIGHT
            elif axis_x < -DEADZONE:
                direction = LEFT
            else:
                direction = STOP
            send_direction(vacuum, direction)
            time.sleep(COMMAND_INTERVAL)
    except KeyboardInterrupt:
        print("Çıkış yapılıyor...")
    finally:
        print("S20 durduruluyor...")
        try:
            send_direction(vacuum, STOP)
            send_direction(vacuum, EXIT)
        except Exception as error:
            print(f"Durdurma komutu gönderilemedi: {error}")
        joystick.quit()
        pygame.quit()


def run() -> None:
    try:
        main()
    except KeyboardInterrupt:
        print("Program kapatıldı.")
    except BaseException as error:
        print(f"\nHATA: {error}")
        print("Ayrıntılı hata:")
        details = traceback.format_exc()
        print(details)
        with open("controller.log", "a", encoding="utf-8") as log_file:
            log_file.write(details + "\n")
    finally:
        try:
            input("\nProgram sonlandı. Bu pencereyi kapatmak için Enter tuşuna basın...")
        except EOFError:
            pass


if __name__ == "__main__":
    run()
