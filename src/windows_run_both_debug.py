from subprocess import Popen, CREATE_NEW_CONSOLE
import os

def main():
	while True:
		try:
			Popen("cmd /c cd tomislav-main/ & python main.py")
			Popen("cmd /c cd tomislav-slave/ & flask run -p 7412")
			input()
		except:
			os.system("taskkill /IM python.exe")
			os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == '__main__':
	main()
