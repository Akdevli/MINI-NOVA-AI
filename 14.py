import os
import subprocess
import webbrowser
import datetime
import pyttsx3
import speech_recognition as sr
import cv2
import requests
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import threading
import wolframalpha
import re
def solve_math_problem(problem):
    """Solve a math problem using WolframAlpha API."""
    app_id = " "  # Replace with your WolframAlpha App ID
    client = wolframalpha.Client(app_id)
    res = client.query(problem)
    try:
        answer = next(res.results).text
        return f"The answer is: {answer}"
    except:
        return "Sorry, I couldn't solve that problem."
def parse_time(time_str):
    """Parse time string in various formats."""
    time_formats = [
        "%I:%M %p",  # 3:30 PM
        "%H:%M",     # 15:30
        "%I %p",     # 3 PM
        "%H"         # 15
    ]
    
    for fmt in time_formats:
        try:
            return datetime.datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    # If no format matches, try to extract hours and minutes
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str, re.I)
    if match:
        hours, minutes, period = match.groups()
        hours = int(hours)
        minutes = int(minutes) if minutes else 0
        
        if period:
            if period.lower() == 'pm' and hours < 12:
                hours += 12
            elif period.lower() == 'am' and hours == 12:
                hours = 0
        
        return datetime.time(hour=hours, minute=minutes)
    
    raise ValueError("Unable to parse time string")

def set_reminder(task, time_str):
    """Set a reminder for a specific task and time."""
    try:
        reminder_time = parse_time(time_str)
        current_time = datetime.datetime.now().time()
        
        # Calculate the time difference
        reminder_datetime = datetime.datetime.combine(datetime.date.today(), reminder_time)
        current_datetime = datetime.datetime.now()
        
        if reminder_datetime <= current_datetime:
            reminder_datetime += datetime.timedelta(days=1)
        
        time_diff = (reminder_datetime - current_datetime).total_seconds()
        
        def remind():
            say(f"Reminder: It's time to {task}")
        
        t = threading.Timer(time_diff, remind)
        t.start()
        return f"Reminder set for {task} at {reminder_time.strftime('%I:%M %p')}"
    except ValueError as e:
        return f"Error setting reminder: {str(e)}"
    

def get_news():
    """Fetch top news headlines."""
    api_key = " "  # Replace with your News API key
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        news = response.json()
        headlines = [article['title'] for article in news['articles'][:5]]
        return "\n".join(headlines)
    else:
        return "Sorry, I couldn't fetch the news at the moment."
    


def get_recipe(dish):
    """Get a simple recipe for a dish."""
    # This is a mock function. In a real application, you'd use a recipe API or database.
    recipes = {
        "pasta": "1. Boil water. 2. Add pasta. 3. Cook for 8-10 minutes. 4. Drain and serve with sauce.",
        "omelette": "1. Beat eggs. 2. Heat pan. 3. Pour eggs. 4. Add fillings. 5. Fold and serve.",
        "smoothie": "1. Add fruits to blender. 2. Add yogurt or milk. 3. Blend until smooth. 4. Serve chilled."
    }
    return recipes.get(dish.lower(), "Sorry, I don't have a recipe for that dish.")


# Initialize translation models for different languages
models = {
    "de": ("Helsinki-NLP/opus-mt-en-de", "translation_en_to_de"),
    "fr": ("Helsinki-NLP/opus-mt-en-fr", "translation_en_to_fr"),
    "es": ("Helsinki-NLP/opus-mt-en-es", "translation_en_to_es"),
    "it": ("Helsinki-NLP/opus-mt-en-it", "translation_en_to_it"),
    "hi": ("Helsinki-NLP/opus-mt-en-hi", "translation_en_to_hi"),
    # Add more languages and models as needed
}

def get_translator(target_language):
    """Load the appropriate model and tokenizer for the target language."""
    model_name, pipeline_task = models.get(target_language, (None, None))
    if model_name:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        return pipeline(pipeline_task, model=model, tokenizer=tokenizer)
    else:
        return None

def translate_text(text, target_languages):
    """Translate text to the target languages."""
    translations = {}
    for lang in target_languages:
        translator = get_translator(lang)
        if translator:
            translation = translator(text)
            translations[lang] = translation[0]['translation_text']
        else:
            translations[lang] = "Translation to this language is not supported."
    return translations

def display_translations(translations):
    """Display translations in a readable format."""
    result_text = "Translations:\n"
    for lang, translated_text in translations.items():
        language_name = [name for name, code in language_map.items() if code == lang][0]
        result_text += f"{language_name.capitalize()}: {translated_text}\n"
    
    # Output to speech
    say(result_text)
    
    # Optionally, save to a file and open it
    try:
        with open("translations.txt", "w", encoding="utf-8") as file:
            file.write(result_text)
        # Open the file with Notepad
        subprocess.Popen(["notepad.exe", "translations.txt"])
    except Exception as e:
        print(f"Error writing to file: {e}")

def open_notepad_and_write(text):
    """Opens Notepad and writes the given text to it."""
    try:
        temp_file = "temp.txt"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(text)
        subprocess.Popen(["notepad.exe", temp_file])
    except Exception as e:
        print("Error opening Notepad:", e)

def voice_command_thread():
    """Thread for continuously listening for voice commands."""
    global command
    while True:
        command = takeCommand()  # Continuously updates the command
        if command:
            print(f"Voice command recognized: {command}")

def open_camera():
    """Opens the default camera and allows user to take photos, record videos, or close the camera using voice commands."""
    cap = cv2.VideoCapture(0)  # 0 for the default camera
    
    # Create folders to save photos and videos if they don't exist
    for folder in ['camera_captures', 'video_recordings']:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    # Initialize speech recognizer
    r = sr.Recognizer()
    
    # Video recording variables
    is_recording = False
    out = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        # Display instructions on the frame
        cv2.putText(frame, "Say: 'capture' for photo, 'record' for video, 'stop' to end recording, 'quit' to close", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        if is_recording:
            cv2.putText(frame, "Recording...", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            out.write(frame)
        
        cv2.imshow('Camera Feed', frame)
        
        # Check for voice commands
        with sr.Microphone() as source:
            try:
                audio = r.listen(source, timeout=1, phrase_time_limit=3)
                command = r.recognize_google(audio, language='en-in').lower()
                print(f"Recognized: {command}")
                
                if 'quit' in command:
                    print("Camera closed by voice command")
                    break
                elif 'capture' in command:
                    # Capture and save the photo
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"camera_captures/photo_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"Photo captured and saved as {filename}")
                    say(f"Photo captured as {filename}")
                elif 'record' in command and not is_recording:
                    # Start video recording
                    is_recording = True
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"video_recordings/video_{timestamp}.avi"
                    fourcc = cv2.VideoWriter_fourcc(*'XVID')
                    out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
                    print(f"Started recording video: {filename}")
                    say("Started video recording")
                elif 'stop' in command and is_recording:
                    # Stop video recording
                    is_recording = False
                    out.release()
                    print("Video recording stopped")
                    say("Video recording stopped")
            except sr.WaitTimeoutError:
                pass  # No speech detected, continue loop
            except sr.UnknownValueError:
                print("Speech not recognized")
            except Exception as e:
                print(f"Error in speech recognition: {e}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Just in case user presses 'q' manually
            break
    
    if is_recording:
        out.release()
    cap.release()
    cv2.destroyAllWindows()

def say(text):
    """Convert text to speech with a female voice."""
    engine = pyttsx3.init()

    # List all voices and find the one with 'Zira' in its name
    voices = engine.getProperty('voices')
    female_voice_id = None
    for voice in voices:
        if 'zira' in voice.name.lower():  # Match voice name containing 'Zira'
            female_voice_id = voice.id
            break

    if female_voice_id:
        engine.setProperty('voice', female_voice_id)
    else:
        print("Microsoft Zira voice not found, using default voice.")

    engine.say(text)
    engine.runAndWait()

def takeCommand(prompt=None):
    """Listen to user input and return recognized text."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if prompt:
            say(prompt)
        audio = r.listen(source)
        try:
            query = r.recognize_google(audio, language='en-in')
            print(f"user said: {query}")
            return query.lower()
        except Exception as e:
            print(f"Error recognizing speech: {e}")
            return None

def get_weather(location, api_token):
    """Fetch current weather for a given location (city, state, or country) using OpenWeatherMap."""
    # OpenWeatherMap API endpoint and parameters
    weather_api_key = api_token  # Replace with your actual API key
    base_url = "https://api.openweathermap.org/data/2.5/weather?"
    params = {"q": location, "appid": weather_api_key, "units": "metric"}
    
    # Make the request to the OpenWeatherMap API
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]
        weather_report = f"The current temperature in {location} is {temp}°C with {description}."
    else:
        weather_report = "Sorry, I couldn't fetch the weather information. Please check the location name."
    
    return weather_report

if __name__ == "__main__":
    say("jai shree krishna, I am NOVA, an artificial intelligence.")
    command=None
    
    
    language_map = {
        "german": "de",
        "french": "fr",
        "spanish": "es",
        "italian": "it",
        "hindi": "hi",
        # Add more mappings as needed
    }
    
    # Replace with your actual OpenWeatherMap API key
    api_token = " "

    while True:
        print("Listening.....")
        query = takeCommand()

        if query:
            # Site opening commands
            if "go to sleep" in query:
                say("ok boss Going to sleep now.")
                break  # Exit the loop and end the program
            
            sites = [["youtube", "https://www.youtube.com"], ["wikipedia", "https://www.wikipedia.com"], ["google", "https://www.google.com"]]
            for site in sites:
                if f"open {site[0]}".lower() in query:
                    say(f"Opening {site[0]} ma'am....")
                    webbrowser.open(site[1])
            
            # Play music
            if "open music" in query:
                say("boss here is your music, i hope u will enjoy")
                musicPath = "C:/Users/hp/Downloads/Big Dawgs - (Raag.Fm).mp3"
                os.startfile(musicPath)
            
            # Tell the time
            elif "time" in query:
                say("ok Boss")
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                say(f"Sir, the time is {current_time}")
            
            # Write in Notepad
            elif "notepad" in query:
                say("What should I write in Notepad?")
                note_text = takeCommand()  # Get text to write from microphone
                if note_text:
                    open_notepad_and_write(note_text)
                    say(f"I've written '{note_text}' in Notepad.")
            

            elif "news" in query:
                news = get_news()
                say("Here are the top headlines:")
                say(news)

            elif "recipe" in query:
                say("What dish would you like a recipe for?")
                dish = takeCommand()
                recipe = get_recipe(dish)
                say(recipe)

            elif "set reminder" in query:
                say("What task should I remind you about?")
                task = takeCommand()
                if task:
                    say("At what time should I remind you?")
                    time_str = takeCommand()
                    if time_str:
                        result = set_reminder(task, time_str)
                        say(result)
                    else:
                        say("Sorry, I didn't catch the time. Please try setting the reminder again.")
                else:
                    say("Sorry, I didn't catch the task. Please try setting the reminder again.")

            #open camera
            elif "open camera" in query:
                open_camera()


            # Translate text
            elif "translate" in query:
                say("Please say the text you want to translate.")
                text_to_translate = takeCommand()
                if text_to_translate:
                    say("Which languages do you want to translate to? example, 'French, Spanish, Hindi'.")
                    languages_input = takeCommand()
                    
                    # Parse the language input
                    target_languages = [language_map.get(lang.strip(), None) for lang in languages_input.split(",")]
                    target_languages = list(filter(None, target_languages))  # Remove None values
                    
                    if not target_languages:
                        say("Sorry, I do not support the specified languages. Please try again.")
                        continue
                    
                    # Translate text
                    translations = translate_text(text_to_translate, target_languages)
                    
                    # Display translations
                    display_translations(translations)

            # Get weather
            elif "weather" in query:
                say("Which location do you want the weather for? ")
                location = takeCommand()
                if location:
                    weather_info = get_weather(location, api_token)
                    say(weather_info)
                    print(weather_info)
            #solve math_problems
            elif "solve math" in query:
                say("What's the math problem?")
                problem = takeCommand()
                solution = solve_math_problem(problem)
                say(solution)