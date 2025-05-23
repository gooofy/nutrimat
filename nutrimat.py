import yaml
import os
import glob
import requests
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
import math
import sys
from datetime import datetime, timedelta # Import timedelta for date calculations

# Initialize Rich Console
console = Console()

# Define the paths for the data files
DATA_DIR = "data"
FOODS_FILE = os.path.join(DATA_DIR, "foods.yaml")
MEALS_FILE = os.path.join(DATA_DIR, "meals.yaml")
ACTIVITIES_FILE = os.path.join(DATA_DIR, "activities.yaml")
DIARY_FILE = os.path.join(DATA_DIR, "diary.yaml")

# Open Food Facts API endpoint
OPENFOODFACTS_API_URL = "https://world.openfoodfacts.org/cgi/search.pl"
SEARCH_PAGE_SIZE = 25 # Increased number of results per page for search display

# --- Data Loading and Saving Functions ---

def load_data(filepath, default_data=None):
    """Loads data from a YAML file."""
    if default_data is None:
        default_data = {}
    if not os.path.exists(filepath):
        console.print(f"[yellow]Warning:[/yellow] Data file not found: {filepath}. Creating empty one.")
        # Ensure the data directory exists before creating the file
        os.makedirs(DATA_DIR, exist_ok=True)
        save_data(filepath, default_data)
        return default_data
    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
            # Ensure loaded data is not None if the file was empty
            return data if data is not None else default_data
    except yaml.YAMLError as e:
        console.print(f"[red]Error loading data from {filepath}:[/red] {e}")
        return default_data

def save_data(filepath, data):
    """Saves data to a YAML file."""
    try:
        # Ensure the data directory exists before saving the file
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(filepath, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
    except yaml.YAMLError as e:
        console.print(f"[red]Error saving data to {filepath}:[/red] {e}")

# --- Command Handlers ---

# Define command aliases
COMMAND_ALIASES = {
    "h": "help",
    "q": "exit",
    "af": "add food",
    "lf": "list foods",
    "df": "delete food",
    "sf": "search food", # Alias for search food
    "am": "add meal", # Alias for add meal
    "lm": "list meals", # Alias for list meals
    "dm": "delete meal", # Alias for delete meal
    "em": "edit meal", # Alias for edit meal
    "aa": "add activity", # Alias for add activity
    "la": "list activities", # Alias for list activities
    "da": "delete activity", # Alias for delete activity
    "ea": "edit activity", # Alias for edit activity
    "l": "log", # Alias for log
    "lfd": "log food", # Alias for log food
    "lml": "log meal", # Alias for log meal
    "lac": "log activity", # Alias for log activity
    "vd": "view day", # Alias for view day
    "rl": "remove log", # Alias for remove log
    "s": "summary", # Alias for summary
}

def handle_help():
    """Displays the help message."""
    console.print("\n[bold]Available Commands:[/bold]")
    console.print("  [green]help[/green] ([cyan]h[/cyan]) - Show this help message")
    console.print("  [green]exit[/green] ([cyan]q[/cyan]) - Exit the application")

    console.print("\n[bold]Food Management:[/bold]")
    console.print("  [green]add food <name> <calories> <fat> <carbs> <protein>[/green] ([cyan]af[/cyan]) - Add a new food item")
    console.print("  [green]list foods \\[pattern][/green] ([cyan]lf \\[pattern][/cyan]) - List all food items (optionally filter by glob pattern)")
    console.print("  [green]delete food <name>[/green] ([cyan]df <name>[/cyan]) - Delete a food item")
    console.print("  [green]search food <query>[/green] ([cyan]sf <query>[/cyan]) - Search for food items in external databases (currently Open Food Facts)")

    console.print("\n[bold]Meal Management:[/bold]")
    console.print("  [green]add meal <name>[/green] ([cyan]am <name>[/cyan]) - Create a new meal definition and enter interactive editor")
    console.print("  [green]list meals[/green] ([cyan]lm[/cyan]) - List all meal definitions")
    console.print("  [green]delete meal <name>[/green] ([cyan]dm <name>[/cyan]) - Delete a meal definition")
    console.print("  [green]edit meal <name>[/green] ([cyan]em <name>[/cyan]) - Edit an existing meal definition in interactive editor")

    console.print("\n[bold]Activity Management:[/bold]")
    console.print("  [green]add activity <name> <calories> <fat> <carbs> <protein>[/green] ([cyan]aa[/cyan]) - Add a new activity item")
    console.print("  [green]list activities \\[pattern][/green] ([cyan]la \\[pattern][/cyan]) - List all activity items (optionally filter by glob pattern)")
    console.print("  [green]delete activity <name>[/green] ([cyan]da <name>[/cyan]) - Delete an activity item")
    console.print("  [green]edit activity <name> <calories> <fat> <carbs> <protein>[/green] ([cyan]ea <name> <calories> <fat> <carbs> <protein>[/cyan]) - Edit an existing activity item")

    console.print("\n[bold]Daily Diary:[/bold]")
    console.print("  [green]log food[/green] ([cyan]lfd[/cyan]) - Log a food item for the current day using a pager")
    console.print("  [green]log meal[/green] ([cyan]lml[/cyan]) - Log a meal for the current day using a pager")
    console.print("  [green]log activity[/green] ([cyan]lac[/cyan]) - Log an activity for the current day using a pager")
    console.print("  [green]view day \\[date][/green] ([cyan]vd \\[date][/cyan]) - View the log and summary for a specific day (YYYY-MM-DD). Defaults to today")
    console.print("  [green]remove log <index>[/green] ([cyan]rl <index>[/cyan]) - Remove an item from the current day's log by its index")
    console.print("  [green]summary <days>[/green] ([cyan]s <days>[/cyan]) - Show a nutritional summary for the last N days")

def handle_exit():
    """Exits the application."""
    console.print("[bold blue]Exiting Nutrition Tracker. Stay healthy![/bold blue]")
    sys.exit() # Use sys.exit() to ensure clean exit

def handle_add_food(app_data, args):
    """Adds a new food item to the food database."""
    parts = args.split()
    if len(parts) != 5:
        console.print("[yellow]Usage:[/yellow] add food <name> <calories> <fat> <carbs> <protein>")
        console.print("[yellow]Alias Usage:[/yellow] af <name> <calories> <fat> <carbs> <protein>")
        return

    name = parts[0].lower() # Store food names in lowercase for case-insensitive lookup
    try:
        calories = float(parts[1])
        fat = float(parts[2])
        carbs = float(parts[3])
        protein = float(parts[4])
    except ValueError:
        console.print("[red]Error:[/red] Calories, fat, carbs, and protein must be numbers.")
        return

    if name in app_data["foods"]:
        console.print(f"[yellow]Warning:[/yellow] Food item '[cyan]{name}[/cyan]' already exists. Use 'delete food' first if you want to replace it.")
        return

    app_data["foods"][name] = {
        "calories": calories,
        "fat": fat,
        "carbs": carbs,
        "protein": protein,
    }
    save_data(FOODS_FILE, app_data["foods"])
    console.print(f"[green]Added food:[/green] [cyan]{name}[/cyan]")

def handle_list_foods(app_data, args=""):
    """Lists all food items in the food database, optionally filtered by a glob pattern."""
    foods = app_data["foods"]
    if not foods:
        console.print("[yellow]No food items found.[/yellow]")
        return

    filter_pattern = args.strip().lower() # Get the filter pattern, lowercase it
    filtered_foods = {}

    if filter_pattern:
        # Filter foods based on the glob pattern
        # We need to match the food names (keys) against the pattern
        matching_names = glob.fnmatch.filter(foods.keys(), filter_pattern)
        for name in matching_names:
            filtered_foods[name] = foods[name]
    else:
        # If no pattern, list all foods
        filtered_foods = foods

    if not filtered_foods:
        console.print(f"[yellow]No food items found matching pattern:[/yellow] [cyan]{filter_pattern}[/cyan]")
        return

    table = Table(title="Local Food Database")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Calories", style="magenta")
    table.add_column("Fat (g)", style="yellow")
    table.add_column("Carbs (g)", style="green")
    table.add_column("Protein (g)", style="blue")

    # Sort filtered foods by name for consistent listing
    for name in sorted(filtered_foods.keys()):
        food = filtered_foods[name]
        table.add_row(
            name,
            f"{food.get('calories', 0):.2f}", # Format to 2 decimal places
            f"{food.get('fat', 0):.2f}",
            f"{food.get('carbs', 0):.2f}",
            f"{food.get('protein', 0):.2f}",
        )

    console.print(table)


def handle_delete_food(app_data, args):
    """Deletes a food item from the food database."""
    name = args.strip().lower()
    if not name:
        console.print("[yellow]Usage:[/yellow] delete food <name>")
        console.print("[yellow]Alias Usage:[/yellow] df <name>")
        return

    if name not in app_data["foods"]:
        console.print(f"[yellow]Warning:[/yellow] Food item '[cyan]{name}[/cyan]' not found.")
        return

    del app_data["foods"][name]
    save_data(FOODS_FILE, app_data["foods"])
    console.print(f"[green]Deleted food:[/green] [cyan]{name}[/cyan]")

def fetch_openfoodfacts_page(query, page):
    """Fetches a specific page of search results from Open Food Facts."""
    params = {
        'search_terms': query,
        'search_simple': 1,
        'action': 'process',
        'json': 1,
        'page_size': SEARCH_PAGE_SIZE,
        'page': page
    }
    response = requests.get(OPENFOODFACTS_API_URL, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get('products', []), data.get('count', 0)


def display_search_results(products, current_page, total_products, total_pages, current_filter):
    """Displays a page of search results in a rich table."""
    if not products:
        console.print(f"[yellow]No results found on page {current_page} matching filter '{current_filter or 'None'}'.[/yellow]")
        return 0 # Return displayed count

    table = Table(title=f"Open Food Facts Search Results (Page {current_page}/{total_pages})")
    table.add_column("Index", style="dim", width=5)
    table.add_column("Product Name", style="cyan", no_wrap=True)
    table.add_column("Quantity", style="magenta")
    table.add_column("Calories (per 100g/ml)", style="yellow")
    table.add_column("Fat (g per 100g/ml)", style="green")
    table.add_column("Carbs (g per 100g/ml)", style="blue")
    table.add_column("Protein (g per 100g/ml)", style="red")

    displayed_count = 0
    # Iterate through the products on the current page and apply the filter
    for i, product in enumerate(products):
        product_name = product.get('product_name', '').strip()

        # Apply filter pattern if provided
        if current_filter and not glob.fnmatch.fnmatch(product_name.lower(), current_filter):
             continue

        # Extract nutritional information per 100g/ml
        nutriments = product.get('nutriments', {})
        calories_100g = nutriments.get('energy-kcal_100g', nutriments.get('energy_kcal_100g', None))
        fat_100g = nutriments.get('fat_100g', None)
        carbs_100g = nutriments.get('carbohydrates_100g', None)
        protein_100g = nutriments.get('proteins_100g', None)

        # Skip entries with N/A for key nutritional values
        if any(val is None or val == '' for val in [calories_100g, fat_100g, carbs_100g, protein_100g]):
             continue

        # Calculate the index for the current displayed page
        display_index = displayed_count + 1

        table.add_row(
            str(display_index), # Display index for the current filtered view
            product_name or 'N/A',
            product.get('quantity', 'N/A'),
            f"{float(calories_100g):.2f}",
            f"{float(fat_100g):.2f}",
            f"{float(carbs_100g):.2f}",
            f"{float(protein_100g):.2f}",
        )
        displayed_count += 1

    if displayed_count > 0:
         console.print(table)
         console.print(f"[italic gray]Showing {displayed_count} results on page {current_page}.[/italic gray]")
         console.print("[italic gray]Nutritional values are per 100g/ml unless otherwise specified.[/italic gray]")
    else:
        console.print(f"[yellow]No results found matching filter:[/yellow] [cyan]{current_filter}[/cyan] on page {current_page}.")

    return displayed_count


def handle_search_food(app_data, args):
    """Searches for food items and enters interactive pager mode."""
    query = args.strip()
    if not query:
        console.print("[yellow]Usage:[/yellow] search food <query>")
        console.print("[yellow]Alias Usage:[/yellow] sf <query>")
        return

    console.print(f"[blue]Searching Open Food Facts for:[/blue] [cyan]{query}[/cyan]...")

    current_page = 1
    current_filter = ""
    all_products = [] # Store all fetched products for the current search session
    total_products = 0
    total_pages = 0

    # Create a separate PromptSession for the pager
    pager_session = PromptSession()


    try:
        # Fetch the first page initially
        products_on_page, total_products = fetch_openfoodfacts_page(query, current_page)
        all_products.extend(products_on_page) # Add to our list of all products
        total_pages = math.ceil(total_products / SEARCH_PAGE_SIZE)

        if not all_products:
            console.print(f"[yellow]No results found for:[/yellow] [cyan]{query}[/cyan]")
            return

        console.print(f"[green]Found {total_products} results.[/green]")

        # Enter interactive pager mode
        while True:
            # first display the search results
            displayed_count = display_search_results(all_products[(current_page - 1) * SEARCH_PAGE_SIZE : current_page * SEARCH_PAGE_SIZE], current_page, total_products, total_pages, current_filter)

            # now display a quick help line in front of the pager prompt
            # Corrected pager commands help text - escaped brackets and added unit/default
            # Escaped the backslash before the square bracket with another backslash
            console.print("\n[bold]Pager Commands:[/bold] [green]n[/green] (next), [green]p[/green] (prev), [green]/ <pattern>[/green] (filter), [green]a <index> <local_name> \\[quantity in grams, default 100g][/green] (add), [green]q[/green] (quit)")
            # Update the pager prompt before getting input
            pager_session.prompt_continuation = f"Pager ({current_page}/{total_pages}, Filter: '{current_filter or 'None'}')> "
            pager_command_line = pager_session.prompt().strip().lower()


            if pager_command_line == 'q':
                console.print("[italic gray]Exiting pager.[/italic gray]")
                break # Exit the pager loop
            elif pager_command_line == 'n':
                if current_page < total_pages:
                    current_page += 1
                    # Fetch the next page if not already fetched
                    if current_page * SEARCH_PAGE_SIZE > len(all_products):
                         console.print(f"[blue]Fetching page {current_page}...[/blue]")
                         try:
                             products_on_page, _ = fetch_openfoodfacts_page(query, current_page)
                             all_products.extend(products_on_page)
                         except requests.exceptions.RequestException as e:
                             console.print(f"[red]Error fetching page {current_page}:[/red] {e}")
                             current_page -= 1 # Stay on the current page
                             continue
                         except Exception as e:
                             console.print(f"[red]An error occurred fetching page {current_page}:[/red] {e}")
                             current_page -= 1 # Stay on the current page
                             continue
                else:
                    console.print("[yellow]Already on the last page.[/yellow]")
            elif pager_command_line == 'p':
                if current_page > 1:
                    current_page -= 1
                else:
                    console.print("[yellow]Already on the first page.[/yellow]")
            elif pager_command_line.startswith('/'):
                current_filter = pager_command_line[1:].strip().lower()
                console.print(f"[italic gray]Filter set to: '{current_filter}'[/italic gray]")
                # No need to change page, just redisplay with the new filter
            elif pager_command_line.startswith('a '):
                 add_args = pager_command_line[2:].strip()
                 add_parts = add_args.split(maxsplit=2)

                 if len(add_parts) < 2:
                      console.print("[yellow]Usage:[/yellow] a <index> <local_name> \\[quantity in grams, default 100g][/yellow]")
                      continue

                 try:
                      # Index refers to the index in the *currently displayed* table
                      display_index = int(add_parts[0])
                      local_name = add_parts[1].strip().lower()
                      quantity_factor = 1.0 # Default quantity factor is 1.0 (for 100g)

                      if len(add_parts) > 2:
                           try:
                                quantity_input = add_parts[2].strip()
                                # Allow specifying quantity in grams directly (e.g., 180)
                                grams = float(quantity_input)
                                quantity_factor = grams / 100.0

                                if quantity_factor <= 0:
                                     console.print("[yellow]Warning:[/yellow] Quantity must be positive. Using default (100g).")
                                     quantity_factor = 1.0

                           except ValueError:
                                console.print("[red]Error:[/red] Invalid quantity. Please provide a number representing grams (e.g., 180).")
                                continue

                 except ValueError:
                      console.print("[red]Error:[/red] Invalid index. Please provide the index from the current search results table.")
                      continue

                 # Find the actual product data based on the display index and current filter/page
                 current_page_products = all_products[(current_page - 1) * SEARCH_PAGE_SIZE : current_page * SEARCH_PAGE_SIZE]
                 filtered_products_on_page = []
                 for product in current_page_products:
                      product_name = product.get('product_name', '').strip()
                      if current_filter and not glob.fnmatch.fnmatch(product_name.lower(), current_filter):
                           continue
                      # Include only products with valid nutritional data for adding
                      nutriments = product.get('nutriments', {})
                      calories_100g = nutriments.get('energy-kcal_100g', nutriments.get('energy_kcal_100g', None))
                      fat_100g = nutriments.get('fat_100g', None)
                      carbs_100g = nutriments.get('carbohydrates_100g', None)
                      protein_100g = nutriments.get('proteins_100g', None)
                      if not any(val is None or val == '' for val in [calories_100g, fat_100g, carbs_100g, protein_100g]):
                           filtered_products_on_page.append(product)


                 if display_index < 1 or display_index > len(filtered_products_on_page):
                      console.print(f"[red]Error:[/red] Invalid index '{display_index}'. Please choose an index from the currently displayed results (1 to {len(filtered_products_on_page)}).")
                      continue

                 # Get the selected product from the filtered list
                 selected_product = filtered_products_on_page[display_index - 1]

                 # Extract nutritional information per 100g/ml
                 nutriments = selected_product.get('nutriments', {})
                 calories_100g = nutriments.get('energy-kcal_100g', nutriments.get('energy_kcal_100g', None))
                 fat_100g = nutriments.get('fat_100g', None)
                 carbs_100g = nutriments.get('carbohydrates_100g', None)
                 protein_100g = nutriments.get('proteins_100g', None)

                 try:
                      # Calculate nutritional values based on the quantity factor
                      calories = float(calories_100g) * quantity_factor
                      fat = float(fat_100g) * quantity_factor
                      carbs = float(carbs_100g) * quantity_factor
                      protein = float(protein_100g) * quantity_factor
                 except ValueError:
                      console.print(f"[red]Error:[/red] Could not process nutritional values for '[cyan]{selected_product.get('product_name', 'N/A')}[/cyan]'. Data might be in an unexpected format.")
                      continue

                 if local_name in app_data["foods"]:
                      console.print(f"[yellow]Warning:[/yellow] Food item '[cyan]{local_name}[/cyan]' already exists in your local database. Use 'delete food' first if you want to replace it.")
                      return

                 app_data["foods"][local_name] = {
                      "calories": calories,
                      "fat": fat,
                      "carbs": carbs,
                      "protein": protein,
                 }
                 save_data(FOODS_FILE, app_data["foods"])
                 console.print(f"[green]Added food from search:[/green] [cyan]{selected_product.get('product_name', 'N/A')}[/cyan] as '[cyan]{local_name}[/cyan]' with quantity [magenta]{quantity_factor * 100:.2f}g[/magenta] to your local database.")

            else:
                console.print(f"[yellow]Unknown pager command:[/yellow] {pager_command_line}. Use 'n', 'p', '/', 'a', or 'q'.")


    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error connecting to Open Food Facts API:[/red] {e}")
    except Exception as e:
        console.print(f"[red]An error occurred during search:[/red] {e}")
        # Optionally print traceback for debugging:
        # import traceback
        # console.print(traceback.format_exc())


# --- Meal Management Handlers ---

def calculate_meal_nutrition(meal_contents, foods_data):
    """Calculates the total nutritional values for a meal."""
    total_calories = 0
    total_fat = 0
    total_carbs = 0
    total_protein = 0

    for item in meal_contents:
        food_name = item["food"]
        # Meal contents now store quantity as pieces
        quantity_pieces = item["quantity"]

        if food_name in foods_data:
            food = foods_data[food_name]
            # Nutritional values are stored per piece/portion in the local database
            total_calories += food.get("calories", 0) * quantity_pieces
            total_fat += food.get("fat", 0) * quantity_pieces
            total_carbs += food.get("carbs", 0) * quantity_pieces
            total_protein += food.get("protein", 0) * quantity_pieces
        else:
            console.print(f"[yellow]Warning:[/yellow] Food item '[cyan]{food_name}[/cyan]' in meal definition not found in local food database. Skipping.")

    return {
        "calories": total_calories,
        "fat": total_fat,
        "carbs": total_carbs,
        "protein": total_protein,
    }


def display_meal_contents(meal_name, meal_contents, foods_data):
    """Displays the contents and nutritional summary of a meal."""
    console.print(f"\n[bold]Meal:[/bold] [cyan]{meal_name}[/cyan]")

    if not meal_contents:
        console.print("[yellow]This meal is currently empty.[/yellow]")
        return

    table = Table(title="Meal Contents")
    table.add_column("Food", style="cyan", no_wrap=True)
    table.add_column("Quantity (pieces)", style="default") # Changed title and style
    # Removed Grams/Piece column
    table.add_column("Calories", style="magenta") # Consistent color (magenta)
    table.add_column("Fat (g)", style="yellow") # Consistent color (yellow)
    table.add_column("Carbs (g)", style="green") # Consistent color (green)
    table.add_column("Protein (g)", style="blue") # Consistent color (blue)

    for item in meal_contents:
        food_name = item["food"]
        quantity_pieces = item["quantity"] # Use quantity (pieces)
        food = foods_data.get(food_name)

        if food:
             # Nutritional values are stored per piece/portion in the local database
             table.add_row(
                 food_name,
                 str(quantity_pieces),
                 f"{food.get('calories', 0) * quantity_pieces:.2f}",
                 f"{food.get('fat', 0) * quantity_pieces:.2f}",
                 f"{food.get('carbs', 0) * quantity_pieces:.2f}",
                 f"{food.get('protein', 0) * quantity_pieces:.2f}",
             )
        else:
             table.add_row(food_name, str(quantity_pieces), "[red]N/A[/red]", "[red]N/A[/red]", "[red]N/A[/red]", "[red]N/A[/red]")


    console.print(table)

    # Display total nutrition
    total_nutrition = calculate_meal_nutrition(meal_contents, foods_data)
    console.print(f"\n[bold]Total Nutrition:[/bold] Calories: [magenta]{total_nutrition['calories']:.2f}[/magenta], Fat: [yellow]{total_nutrition['fat']:.2f}g[/yellow], Carbs: [green]{total_nutrition['carbs']:.2f}g[/green], Protein: [blue]{total_nutrition['protein']:.2f}g[/blue]") # Consistent colors


def run_meal_editor(app_data, meal_name, initial_contents):
    """Runs the interactive meal editor session."""
    console.print(f"\n[bold green]Entering editor for meal:[/bold green] [cyan]{meal_name}[/cyan]")
    console.print("Type '[green]help[/green]' for editor commands.")

    # Create a mutable copy of the initial contents
    current_meal_contents = initial_contents[:]

    meal_editor_session = PromptSession(f"Meal Editor ({meal_name})> ")

    while True:
        display_meal_contents(meal_name, current_meal_contents, app_data["foods"])

        # Updated editor commands help text - removed save/discard
        # Escaped the backslash before the square bracket with another backslash
        console.print("\n[bold]Editor Commands:[/bold] [green]list \\[pattern][/green], [green]add <food_name> <pieces>[/green], [green]delete <food_name>[/green], [green]help[/green], [green]quit[/green]")
        editor_command_line = meal_editor_session.prompt().strip().lower()

        if editor_command_line == 'quit' or editor_command_line == 'q':
             # Save changes automatically on quit
             app_data["meals"][meal_name] = current_meal_contents
             save_data(MEALS_FILE, app_data["meals"])
             console.print(f"[green]Meal '[cyan]{meal_name}[/cyan]' saved automatically on exit.[/green]")
             break # Exit the editor loop
        elif editor_command_line == 'help' or editor_command_line == 'h':
             console.print("\n[bold]Meal Editor Commands:[/bold]")
             # escape [
             console.print("  [green]list \\[pattern][/green] ([cyan]l [pattern][/cyan]) - List food items in your local database (optionally filter).")
             console.print("  [green]add <food_name> <pieces>[/green] ([cyan]a <food_name> <pieces>[/cyan]) - Add a food item with quantity in pieces to this meal.")
             console.print("  [green]delete <food_name>[/green] ([cyan]d <food_name>[/cyan]) - Remove a food item from this meal.")
             # Removed save/discard from help text
             console.print("  [green]help[/green] ([cyan]h[/cyan]) - Show this help message.")
             console.print("  [green]quit[/green] ([cyan]q[/cyan]) - Save changes and exit the editor.") # Updated help text
        elif editor_command_line.startswith('list') or editor_command_line.startswith('l'):
            # Pass the rest of the args as filter pattern to handle_list_foods
            list_args = editor_command_line.split(maxsplit=1)[1] if len(editor_command_line.split(maxsplit=1)) > 1 else ""
            handle_list_foods(app_data, list_args.strip()) # Reuse the existing list foods handler with filter
        elif editor_command_line.startswith('add ') or editor_command_line.startswith('a '):
            add_args = editor_command_line.split(maxsplit=2) # Split into food_name, pieces
            if len(add_args) != 3: # Expecting 2 arguments after 'add' or 'a'
                console.print("[yellow]Usage:[/yellow] add <food_name> <pieces>") # Updated usage
                continue
            food_name = add_args[1].strip().lower()
            pieces_str = add_args[2].strip()

            if food_name not in app_data["foods"]:
                 console.print(f"[red]Error:[/red] Food item '[cyan]{food_name}[/cyan]' not found in your local food database.")
                 continue

            try:
                quantity_pieces = int(pieces_str)
                if quantity_pieces <= 0:
                    console.print("[red]Error:[/red] Number of pieces must be a positive integer.")
                    continue
            except ValueError:
                console.print("[red]Error:[/red] Invalid number of pieces. Please provide an integer.")
                continue

            # Check if the food is already in the meal and update quantity
            found = False
            for item in current_meal_contents:
                 if item["food"] == food_name:
                      item["quantity"] += quantity_pieces # Add pieces
                      found = True
                      console.print(f"[green]Updated quantity for food:[/green] [cyan]{food_name}[/cyan] to [magenta]{item['quantity']}[/magenta] pieces.")
                      break
            if not found:
                current_meal_contents.append({"food": food_name, "quantity": quantity_pieces}) # Store pieces
                console.print(f"[green]Added food:[/green] [cyan]{food_name}[/cyan] with [magenta]{quantity_pieces}[/magenta] pieces to the meal.")

        elif editor_command_line.startswith('delete ') or editor_command_line.startswith('d '):
             delete_args = editor_command_line.split(maxsplit=1)
             if len(delete_args) != 2:
                  console.print("[yellow]Usage:[/yellow] delete <food_name>")
                  continue
             food_name_to_delete = delete_args[1].strip().lower()
             original_count = len(current_meal_contents)
             # Filter out the food item to delete
             current_meal_contents = [item for item in current_meal_contents if item["food"] != food_name_to_delete]
             if len(current_meal_contents) < original_count:
                  console.print(f"[green]Removed food:[/green] [cyan]{food_name_to_delete}[/cyan] from the meal.")
             else:
                  console.print(f"[yellow]Warning:[/yellow] Food item '[cyan]{food_name_to_delete}[/cyan]' not found in the meal.")

        # Removed elif for 'save' command
        # Removed elif for 'discard' command
        else:
            console.print(f"[yellow]Unknown editor command:[/yellow] {editor_command_line}. Type '[green]help[/green]' for a list of commands.")


def handle_add_meal(app_data, args):
    """Initiates the interactive editor for a new meal."""
    meal_name = args.strip().lower()
    if not meal_name:
        console.print("[yellow]Usage:[/yellow] add meal <name>")
        console.print("[yellow]Alias Usage:[/yellow] am <name>")
        return

    if meal_name in app_data["meals"]:
        console.print(f"[yellow]Warning:[/yellow] Meal '[cyan]{meal_name}[/cyan]' already exists. Use 'edit meal' if you want to modify it.")
        return

    # Start the meal editor with empty contents for a new meal
    run_meal_editor(app_data, meal_name, [])


def handle_list_meals(app_data):
    """Lists all meal definitions in the meal database."""
    meals = app_data["meals"]
    if not meals:
        console.print("[yellow]No meal definitions found.[/yellow]")
        return

    table = Table(title="Meal Definitions")
    table.add_column("Meal Name", style="cyan", no_wrap=True)
    # Set a max width for the Contents column and enable overflow ellipsis, also set no_wrap=True to make this work
    table.add_column("Contents", style="red", width=40, overflow="ellipsis", no_wrap=True)
    table.add_column("Calories", style="magenta")
    table.add_column("Fat (g)", style="yellow")
    table.add_column("Carbs (g)", style="green")
    table.add_column("Protein (g)", style="blue")

    # Sort meals by name for consistent listing
    for meal_name in sorted(meals.keys()):
        contents = meals[meal_name]
        # Display quantity as pieces in the list meals output
        content_str = ", ".join([f"{item['food']} ({item['quantity']} pcs)" for item in contents])
        total_nutrition = calculate_meal_nutrition(contents, app_data["foods"])
        table.add_row(
            meal_name,
            content_str, # The truncation is handled by the column definition
            f"{total_nutrition['calories']:.2f}",
            f"{total_nutrition['fat']:.2f}",
            f"{total_nutrition['carbs']:.2f}",
            f"{total_nutrition['protein']:.2f}",
        )

    console.print(table)


def handle_delete_meal(app_data, args):
    """Deletes a meal definition from the meal database."""
    meal_name = args.strip().lower()
    if not meal_name:
        console.print("[yellow]Usage:[/yellow] delete meal <name>")
        console.print("[yellow]Alias Usage:[/yellow] dm <name>")
        return

    if meal_name not in app_data["meals"]:
        console.print(f"[yellow]Warning:[/yellow] Meal '[cyan]{meal_name}[/cyan]' not found.")
        return

    del app_data["meals"][meal_name]
    save_data(MEALS_FILE, app_data["meals"])
    console.print(f"[green]Deleted meal:[/green] [cyan]{meal_name}[/cyan]")


def handle_edit_meal(app_data, args):
    """Initiates the interactive editor for an existing meal."""
    meal_name = args.strip().lower()
    if not meal_name:
        console.print("[yellow]Usage:[/yellow] edit meal <name>")
        console.print("[yellow]Alias Usage:[/yellow] em <name>")
        return

    if meal_name not in app_data["meals"]:
        console.print(f"[red]Error:[/red] Meal '[cyan]{meal_name}[/cyan]' not found.")
        return

    # Start the meal editor with the existing meal contents
    # Create a deep copy to avoid modifying the original data in app_data directly
    import copy
    run_meal_editor(app_data, meal_name, copy.deepcopy(app_data["meals"][meal_name]))

# --- Activity Management Handlers ---

def handle_add_activity(app_data, args):
    """Adds a new activity item to the activity database."""
    parts = args.split()
    if len(parts) != 5:
        console.print("[yellow]Usage:[/yellow] add activity <name> <calories> <fat> <carbs> <protein>")
        console.print("[yellow]Alias Usage:[/yellow] aa <name> <calories> <fat> <carbs> <protein>")
        return

    name = parts[0].lower() # Store activity names in lowercase for case-insensitive lookup
    try:
        calories = float(parts[1])
        fat = float(parts[2])
        carbs = float(parts[3])
        protein = float(parts[4])
    except ValueError:
        console.print("[red]Error:[/red] Calories, fat, carbs, and protein must be numbers.")
        return

    if name in app_data["activities"]:
        console.print(f"[yellow]Warning:[/yellow] Activity '[cyan]{name}[/cyan]' already exists. Use 'delete activity' first if you want to replace it.")
        return

    app_data["activities"][name] = {
        "calories": calories,
        "fat": fat,
        "carbs": carbs,
        "protein": protein,
    }
    save_data(ACTIVITIES_FILE, app_data["activities"])
    console.print(f"[green]Added activity:[/green] [cyan]{name}[/cyan]")


def handle_list_activities(app_data, args=""):
    """Lists all activity items in the activity database, optionally filtered by a glob pattern."""
    activities = app_data["activities"]
    if not activities:
        console.print("[yellow]No activity items found.[/yellow]")
        return

    filter_pattern = args.strip().lower() # Get the filter pattern, lowercase it
    filtered_activities = {}

    if filter_pattern:
        # Filter activities based on the glob pattern
        # We need to match the activity names (keys) against the pattern
        matching_names = glob.fnmatch.filter(activities.keys(), filter_pattern)
        for name in matching_names:
            filtered_activities[name] = activities[name]
    else:
        # If no pattern, list all activities
        filtered_activities = activities

    if not filtered_activities:
        console.print(f"[yellow]No activity items found matching pattern:[/yellow] [cyan]{filter_pattern}[/cyan]")
        return


    table = Table(title="Activity Database (Calories/Macros Burned)")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Calories", style="magenta")
    table.add_column("Fat (g)", style="yellow")
    table.add_column("Carbs (g)", style="green")
    table.add_column("Protein (g)", style="blue")

    # Sort filtered activities by name for consistent listing
    for name in sorted(filtered_activities.keys()):
        activity = filtered_activities[name]
        table.add_row(
            name,
            f"{activity.get('calories', 0):.2f}", # Format to 2 decimal places
            f"{activity.get('fat', 0):.2f}",
            f"{activity.get('carbs', 0):.2f}",
            f"{activity.get('protein', 0):.2f}",
        )

    console.print(table)


def handle_delete_activity(app_data, args):
    """Deletes an activity item from the activity database."""
    name = args.strip().lower()
    if not name:
        console.print("[yellow]Usage:[/yellow] delete activity <name>")
        console.print("[yellow]Alias Usage:[/yellow] da <name>")
        return

    if name not in app_data["activities"]:
        console.print(f"[yellow]Warning:[/yellow] Activity '[cyan]{name}[/cyan]' not found.")
        return

    del app_data["activities"][name]
    save_data(ACTIVITIES_FILE, app_data["activities"])
    console.print(f"[green]Deleted activity:[/green] [cyan]{name}[/cyan]")


def handle_edit_activity(app_data, args):
    """Edits an existing activity item in the activity database."""
    parts = args.split()
    if len(parts) != 5:
        console.print("[yellow]Usage:[/yellow] edit activity <name> <calories> <fat> <carbs> <protein>")
        console.print("[yellow]Alias Usage:[/yellow] ea <name> <calories> <fat> <carbs> <protein>")
        return

    name = parts[0].lower() # Activity name to edit
    try:
        calories = float(parts[1])
        fat = float(parts[2])
        carbs = float(parts[3])
        protein = float(parts[4])
    except ValueError:
        console.print("[red]Error:[/red] Calories, fat, carbs, and protein must be numbers.")
        return

    if name not in app_data["activities"]:
        console.print(f"[red]Error:[/red] Activity '[cyan]{name}[/cyan]' not found.")
        return

    app_data["activities"][name] = {
        "calories": calories,
        "fat": fat,
        "carbs": carbs,
        "protein": protein,
    }
    save_data(ACTIVITIES_FILE, app_data["activities"])
    console.print(f"[green]Edited activity:[/green] [cyan]{name}[/cyan]")

# --- Daily Diary Handlers ---

def get_current_date_str():
    """Returns the current date as a YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")

def calculate_day_nutrition(day_entries, app_data):
    """Calculates the total nutritional values for a given day's entries."""
    total_calories = 0
    total_fat = 0
    total_carbs = 0
    total_protein = 0

    for entry in day_entries:
        item_type = entry["type"]
        item_name = entry["name"]
        quantity = entry["quantity"]

        if item_type == "food":
            if item_name in app_data["foods"]:
                food = app_data["foods"][item_name]
                total_calories += food.get("calories", 0) * quantity
                total_fat += food.get("fat", 0) * quantity
                total_carbs += food.get("carbs", 0) * quantity
                total_protein += food.get("protein", 0) * quantity
            else:
                console.print(f"[yellow]Warning:[/yellow] Food item '[cyan]{item_name}[/cyan]' in diary entry not found in local food database. Skipping.")
        elif item_type == "meal":
            if item_name in app_data["meals"]:
                meal_contents = app_data["meals"][item_name]
                # Calculate nutrition for the meal contents and multiply by meal quantity
                meal_nutrition = calculate_meal_nutrition(meal_contents, app_data["foods"])
                total_calories += meal_nutrition["calories"] * quantity
                total_fat += meal_nutrition["fat"] * quantity
                total_carbs += meal_nutrition["carbs"] * quantity
                total_protein += meal_nutrition["protein"] * quantity
            else:
                console.print(f"[yellow]Warning:[/yellow] Meal '[cyan]{item_name}[/cyan]' in diary entry not found in local meal database. Skipping.")
        elif item_type == "activity":
            if item_name in app_data["activities"]:
                activity = app_data["activities"][item_name]
                # Activities subtract from totals, so use negative values
                total_calories -= activity.get("calories", 0) * quantity
                total_fat -= activity.get("fat", 0) * quantity
                total_carbs -= activity.get("carbs", 0) * quantity
                total_protein -= activity.get("protein", 0) * quantity
            else:
                console.print(f"[yellow]Warning:[/yellow] Activity '[cyan]{item_name}[/cyan]' in diary entry not found in local activity database. Skipping.")

    return {
        "calories": total_calories,
        "fat": total_fat,
        "carbs": total_carbs,
        "protein": total_protein,
    }


def display_day_log(date_str, day_entries, app_data):
    """Displays the log and nutritional summary for a specific day."""
    console.print(f"\n[bold]Daily Log for:[/bold] [cyan]{date_str}[/cyan]")

    if not day_entries:
        console.print("[yellow]No entries logged for this day.[/yellow]")
        return

    table = Table(title="Logged Items")
    table.add_column("Index", style="dim", width=5)
    table.add_column("Type", style="magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Quantity", style="default")
    table.add_column("Calories", style="magenta") # Consistent color
    table.add_column("Fat (g)", style="yellow") # Consistent color
    table.add_column("Carbs (g)", style="green") # Consistent color
    table.add_column("Protein (g)", style="blue") # Consistent color

    for i, entry in enumerate(day_entries):
        item_type = entry["type"]
        item_name = entry["name"]
        quantity = entry["quantity"]
        calories = 0
        fat = 0
        carbs = 0
        protein = 0

        # Calculate nutrition for the individual item for display
        if item_type == "food":
            if item_name in app_data["foods"]:
                food = app_data["foods"][item_name]
                calories = food.get("calories", 0) * quantity
                fat = food.get("fat", 0) * quantity
                carbs = food.get("carbs", 0) * quantity
                protein = food.get("protein", 0) * quantity
        elif item_type == "meal":
            if item_name in app_data["meals"]:
                meal_contents = app_data["meals"][item_name]
                meal_nutrition = calculate_meal_nutrition(meal_contents, app_data["foods"])
                calories = meal_nutrition["calories"] * quantity
                fat = meal_nutrition["fat"] * quantity
                carbs = meal_nutrition["carbs"] * quantity
                protein = meal_nutrition["protein"] * quantity
        elif item_type == "activity":
             if item_name in app_data["activities"]:
                  activity = app_data["activities"][item_name]
                  # Display burned calories/macros as negative
                  calories = -activity.get("calories", 0) * quantity
                  fat = -activity.get("fat", 0) * quantity
                  carbs = -activity.get("carbs", 0) * quantity
                  protein = -activity.get("protein", 0) * quantity


        table.add_row(
            str(i + 1), # Display index starting from 1
            item_type.capitalize(),
            item_name,
            str(quantity),
            f"{calories:.2f}",
            f"{fat:.2f}",
            f"{carbs:.2f}",
            f"{protein:.2f}",
        )

    console.print(table)

    # Display total nutrition for the day
    total_nutrition = calculate_day_nutrition(day_entries, app_data)
    console.print(f"\n[bold]Day Totals:[/bold] Calories: [magenta]{total_nutrition['calories']:.2f}[/magenta], Fat: [yellow]{total_nutrition['fat']:.2f}g[/yellow], Carbs: [green]{total_nutrition['carbs']:.2f}g[/green], Protein: [blue]{total_nutrition['protein']:.2f}g[/blue]")


def handle_log_food(app_data):
    """Logs a food item for the current day using a pager."""
    foods = app_data["foods"]
    if not foods:
        console.print("[yellow]No food items found in your local database.[/yellow]")
        return

    # Convert foods to a list for indexed access
    food_list = sorted(foods.items(), key=lambda x: x[0])  # Sort by name
    pager_session = PromptSession()

    current_page = 1
    items_per_page = 10
    total_pages = (len(food_list) + items_per_page - 1) // items_per_page

    while True:
        # Display the current page
        start_index = (current_page - 1) * items_per_page
        end_index = start_index + items_per_page
        page_items = food_list[start_index:end_index]

        table = Table(title=f"Food Database (Page {current_page}/{total_pages})")
        table.add_column("Index", style="dim", width=5)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Calories", style="magenta")
        table.add_column("Fat (g)", style="yellow")
        table.add_column("Carbs (g)", style="green")
        table.add_column("Protein (g)", style="blue")

        for i, (name, food) in enumerate(page_items, start=start_index + 1):
            table.add_row(
                str(i),
                name,
                f"{food.get('calories', 0):.2f}",
                f"{food.get('fat', 0):.2f}",
                f"{food.get('carbs', 0):.2f}",
                f"{food.get('protein', 0):.2f}",
            )

        console.print(table)

        # Prompt for user input
        console.print("[bold]Commands:[/bold] [green]n[/green] (next), [green]p[/green] (prev), [green]q[/green] (quit), [green]<index>[/green] (select item)")
        command = pager_session.prompt(f"Select a food (Page {current_page}/{total_pages})> ").strip().lower()

        if command == "q":
            console.print("[italic gray]Exiting food log pager.[/italic gray]")
            break
        elif command == "n":
            if current_page < total_pages:
                current_page += 1
            else:
                console.print("[yellow]Already on the last page.[/yellow]")
        elif command == "p":
            if current_page > 1:
                current_page -= 1
            else:
                console.print("[yellow]Already on the first page.[/yellow]")
        elif command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(food_list):
                selected_food = food_list[index]
                name = selected_food[0]
                console.print(f"[green]Selected food:[/green] [cyan]{name}[/cyan]")

                # Prompt for quantity
                quantity_str = pager_session.prompt(f"Enter quantity for [cyan]{name}[/cyan] (in pieces)> ").strip()
                try:
                    quantity = int(quantity_str)
                    if quantity <= 0:
                        console.print("[red]Error:[/red] Quantity must be a positive integer.")
                        continue
                except ValueError:
                    console.print("[red]Error:[/red] Invalid quantity. Please enter a positive integer.")
                    continue

                # Log the food
                current_date_str = get_current_date_str()
                if current_date_str not in app_data["diary"]:
                    app_data["diary"][current_date_str] = []

                app_data["diary"][current_date_str].append({
                    "type": "food",
                    "name": name,
                    "quantity": quantity,
                })
                save_data(DIARY_FILE, app_data["diary"])
                console.print(f"[green]Logged {quantity} x {name} (food) for today.[/green]")
                break
            else:
                console.print("[red]Error:[/red] Invalid index. Please select a valid index.")
        else:
            console.print("[yellow]Unknown command. Use 'n', 'p', 'q', or an index to select an item.[/yellow]")

def handle_log_meal(app_data):
    """Logs a meal for the current day using a pager."""
    meals = app_data["meals"]
    if not meals:
        console.print("[yellow]No meal definitions found in your local database.[/yellow]")
        return

    # Convert meals to a list for indexed access
    meal_list = sorted(meals.items(), key=lambda x: x[0])  # Sort by name
    pager_session = PromptSession()

    current_page = 1
    items_per_page = 10
    total_pages = (len(meal_list) + items_per_page - 1) // items_per_page

    while True:
        # Display the current page
        start_index = (current_page - 1) * items_per_page
        end_index = start_index + items_per_page
        page_items = meal_list[start_index:end_index]

        table = Table(title=f"Meal Database (Page {current_page}/{total_pages})")
        table.add_column("Index", style="dim", width=5)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Contents", style="magenta", width=40, overflow="ellipsis", no_wrap=True)

        for i, (name, contents) in enumerate(page_items, start=start_index + 1):
            content_str = ", ".join([f"{item['food']} ({item['quantity']} pcs)" for item in contents])
            table.add_row(str(i), name, content_str)

        console.print(table)

        # Prompt for user input
        console.print("[bold]Commands:[/bold] [green]n[/green] (next), [green]p[/green] (prev), [green]q[/green] (quit), [green]<index>[/green] (select item)")
        command = pager_session.prompt(f"Select a meal (Page {current_page}/{total_pages})> ").strip().lower()

        if command == "q":
            console.print("[italic gray]Exiting meal log pager.[/italic gray]")
            break
        elif command == "n":
            if current_page < total_pages:
                current_page += 1
            else:
                console.print("[yellow]Already on the last page.[/yellow]")
        elif command == "p":
            if current_page > 1:
                current_page -= 1
            else:
                console.print("[yellow]Already on the first page.[/yellow]")
        elif command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(meal_list):
                selected_meal = meal_list[index]
                name = selected_meal[0]
                console.print(f"[green]Selected meal:[/green] [cyan]{name}[/cyan]")

                # Prompt for quantity
                quantity_str = pager_session.prompt(f"Enter quantity for [cyan]{name}[/cyan] (in servings)> ").strip()
                try:
                    quantity = int(quantity_str)
                    if quantity <= 0:
                        console.print("[red]Error:[/red] Quantity must be a positive integer.")
                        continue
                except ValueError:
                    console.print("[red]Error:[/red] Invalid quantity. Please enter a positive integer.")
                    continue

                # Log the meal
                current_date_str = get_current_date_str()
                if current_date_str not in app_data["diary"]:
                    app_data["diary"][current_date_str] = []

                app_data["diary"][current_date_str].append({
                    "type": "meal",
                    "name": name,
                    "quantity": quantity,
                })
                save_data(DIARY_FILE, app_data["diary"])
                console.print(f"[green]Logged {quantity} x {name} (meal) for today.[/green]")
                break
            else:
                console.print("[red]Error:[/red] Invalid index. Please select a valid index.")
        else:
            console.print("[yellow]Unknown command. Use 'n', 'p', 'q', or an index to select an item.[/yellow]")

def handle_log_activity(app_data):
    """Logs an activity for the current day using a pager."""
    activities = app_data["activities"]
    if not activities:
        console.print("[yellow]No activity items found in your local database.[/yellow]")
        return

    # Convert activities to a list for indexed access
    activity_list = sorted(activities.items(), key=lambda x: x[0])  # Sort by name
    pager_session = PromptSession()

    current_page = 1
    items_per_page = 10
    total_pages = (len(activity_list) + items_per_page - 1) // items_per_page

    while True:
        # Display the current page
        start_index = (current_page - 1) * items_per_page
        end_index = start_index + items_per_page
        page_items = activity_list[start_index:end_index]

        table = Table(title=f"Activity Database (Page {current_page}/{total_pages})")
        table.add_column("Index", style="dim", width=5)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Calories", style="magenta")
        table.add_column("Fat (g)", style="yellow")
        table.add_column("Carbs (g)", style="green")
        table.add_column("Protein (g)", style="blue")

        for i, (name, activity) in enumerate(page_items, start=start_index + 1):
            table.add_row(
                str(i),
                name,
                f"{activity.get('calories', 0):.2f}",
                f"{activity.get('fat', 0):.2f}",
                f"{activity.get('carbs', 0):.2f}",
                f"{activity.get('protein', 0):.2f}",
            )

        console.print(table)

        # Prompt for user input
        console.print("[bold]Commands:[/bold] [green]n[/green] (next), [green]p[/green] (prev), [green]q[/green] (quit), [green]<index>[/green] (select item)")
        command = pager_session.prompt(f"Select an activity (Page {current_page}/{total_pages})> ").strip().lower()

        if command == "q":
            console.print("[italic gray]Exiting activity log pager.[/italic gray]")
            break
        elif command == "n":
            if current_page < total_pages:
                current_page += 1
            else:
                console.print("[yellow]Already on the last page.[/yellow]")
        elif command == "p":
            if current_page > 1:
                current_page -= 1
            else:
                console.print("[yellow]Already on the first page.[/yellow]")
        elif command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(activity_list):
                selected_activity = activity_list[index]
                name = selected_activity[0]
                console.print(f"[green]Selected activity:[/green] [cyan]{name}[/cyan]")

                # Prompt for quantity
                quantity_str = pager_session.prompt(f"Enter quantity for [cyan]{name}[/cyan] (in repetitions)> ").strip()
                try:
                    quantity = int(quantity_str)
                    if quantity <= 0:
                        console.print("[red]Error:[/red] Quantity must be a positive integer.")
                        continue
                except ValueError:
                    console.print("[red]Error:[/red] Invalid quantity. Please enter a positive integer.")
                    continue

                # Log the activity
                current_date_str = get_current_date_str()
                if current_date_str not in app_data["diary"]:
                    app_data["diary"][current_date_str] = []

                app_data["diary"][current_date_str].append({
                    "type": "activity",
                    "name": name,
                    "quantity": quantity,
                })
                save_data(DIARY_FILE, app_data["diary"])
                console.print(f"[green]Logged {quantity} x {name} (activity) for today.[/green]")
                break
            else:
                console.print("[red]Error:[/red] Invalid index. Please select a valid index.")
        else:
            console.print("[yellow]Unknown command. Use 'n', 'p', 'q', or an index to select an item.[/yellow]")


def handle_view_day(app_data, args):
    """Views the log and summary for a specific day."""
    date_str = args.strip()
    if not date_str:
        # Default to today if no date is provided
        date_str = get_current_date_str()

    # Validate date format (basic YYYY-MM-DD check)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Error:[/red] Invalid date format. Please use YYYY-MM-DD.")
        return

    if date_str not in app_data["diary"]:
        console.print(f"[yellow]No diary entries found for date:[/yellow] [cyan]{date_str}[/cyan]")
        return

    display_day_log(date_str, app_data["diary"][date_str], app_data)


def handle_remove_log(app_data, args):
    """Removes an item from the current day's log by index."""
    current_date_str = get_current_date_str()

    if current_date_str not in app_data["diary"] or not app_data["diary"][current_date_str]:
        console.print("[yellow]No entries logged for today to remove.[/yellow]")
        return

    # Display the current day's log with indices first
    display_day_log(current_date_str, app_data["diary"][current_date_str], app_data)

    index_str = args.strip()
    if not index_str:
        console.print("[yellow]Usage:[/yellow] remove log <index>")
        console.print("[yellow]Alias Usage:[/yellow] rl <index>")
        return

    try:
        index_to_remove = int(index_str) - 1 # Adjust for 0-based indexing
        if index_to_remove < 0 or index_to_remove >= len(app_data["diary"][current_date_str]):
            console.print(f"[red]Error:[/red] Invalid index. Please provide a valid index from the list (1 to {len(app_data['diary'][current_date_str])}).")
            return
    except ValueError:
        console.print("[red]Error:[/red] Invalid index. Please provide an integer index.")
        return

    removed_item = app_data["diary"][current_date_str].pop(index_to_remove)
    save_data(DIARY_FILE, app_data["diary"])
    console.print(f"[green]Removed item at index {index_str}:[/green] {removed_item['quantity']} x {removed_item['name']} ({removed_item['type']}).")
    # Optionally display the updated log
    # display_day_log(current_date_str, app_data["diary"][current_date_str], app_data)


def handle_summary(app_data, args):
    """Shows a nutritional summary for the last N days."""
    days_str = args.strip()
    if not days_str:
        console.print("[yellow]Usage:[/yellow] summary <days>")
        console.print("[yellow]Alias Usage:[/yellow] s <days>")
        return

    try:
        num_days = int(days_str)
        if num_days <= 0:
            console.print("[red]Error:[/red] Number of days must be a positive integer.")
            return
    except ValueError:
        console.print("[red]Error:[/red] Invalid number of days. Please provide an integer.")
        return

    today = datetime.now().date()
    total_calories = 0
    total_fat = 0
    total_carbs = 0
    total_protein = 0
    days_with_entries = 0

    console.print(f"\n[bold]Nutritional Summary for the Last {num_days} Days:[/bold]")

    for i in range(num_days):
        current_date = today - timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")

        if date_str in app_data["diary"] and app_data["diary"][date_str]:
            days_with_entries += 1
            day_nutrition = calculate_day_nutrition(app_data["diary"][date_str], app_data)
            total_calories += day_nutrition["calories"]
            total_fat += day_nutrition["fat"]
            total_carbs += day_nutrition["carbs"]
            total_protein += day_nutrition["protein"]
            console.print(f"  [cyan]{date_str}:[/cyan] Calories: [magenta]{day_nutrition['calories']:.2f}[/magenta], Fat: [yellow]{day_nutrition['fat']:.2f}g[/yellow], Carbs: [green]{day_nutrition['carbs']:.2f}g[/green], Protein: [blue]{day_nutrition['protein']:.2f}g[/blue]")


    if days_with_entries > 0:
        console.print("\n[bold]Average Daily Totals (over days with entries):[/bold]")
        console.print(f"  Calories: [magenta]{total_calories / days_with_entries:.2f}[/magenta]")
        console.print(f"  Fat: [yellow]{total_fat / days_with_entries:.2f}g[/yellow]")
        console.print(f"  Carbs: [green]{total_carbs / days_with_entries:.2f}g[/green]")
        console.print(f"  Protein: [blue]{total_protein / days_with_entries:.2f}g[/blue]")
    else:
        console.print("[yellow]No diary entries found in the last specified days.[/yellow]")


# --- Main Application Loop ---

def run_tracker():
    """Runs the main application loop."""
    console.print("[bold cyan]Welcome to the Nutrition Tracker![/bold cyan]")
    console.print("Type '[green]help[/green]' for available commands.")

    # Load initial data (will be empty if files don't exist)
    foods_data = load_data(FOODS_FILE)
    meals_data = load_data(MEALS_FILE)
    activities_data = load_data(ACTIVITIES_FILE) # Load activities data
    diary_data = load_data(DIARY_FILE) # Load diary data

    # This is where we will store the data in memory while the app runs
    app_data = {
        "foods": foods_data,
        "meals": meals_data,
        "activities": activities_data, # Include activities in app_data
        "diary": diary_data, # Include diary in app_data
        "last_search_results": [] # This is no longer strictly necessary for the pager, but keeping for now
    }

    # Create the main PromptSession
    main_session = PromptSession("> ")

    while True:
        try:
            # Get user input using prompt_toolkit from the main session
            command_line = main_session.prompt().strip()
            if not command_line:
                # Display current day's summary if input is empty
                current_date_str = get_current_date_str()
                if current_date_str in app_data["diary"] and app_data["diary"][current_date_str]:
                     console.print("\n[bold]Today's Summary:[/bold]")
                     today_nutrition = calculate_day_nutrition(app_data["diary"][current_date_str], app_data)
                     console.print(f"  Calories: [magenta]{today_nutrition['calories']:.2f}[/magenta], Fat: [yellow]{today_nutrition['fat']:.2f}g[/yellow], Carbs: [green]{today_nutrition['carbs']:.2f}g[/green], Protein: [blue]{today_nutrition['protein']:.2f}g[/blue]")
                else:
                     console.print("[italic gray]No entries logged for today.[/italic gray]")
                continue # Skip empty input after displaying summary

            # --- Alias Handling ---
            # Check if the command is an alias and expand it
            parts = command_line.split(maxsplit=1)
            command_part = parts[0].lower()
            if command_part in COMMAND_ALIASES:
                expanded_command = COMMAND_ALIASES[command_part]
                # Reconstruct the command line with the expanded command and original arguments
                command_line = expanded_command + (f" {parts[1]}" if len(parts) > 1 else "")
                console.print(f"[italic gray](Alias expanded to: {command_line})[/italic gray]") # Optional: show expansion

            # --- Command Processing ---
            parts = command_line.split(maxsplit=1)
            command = parts[0].lower() # Process command in lowercase
            args = parts[1] if len(parts) > 1 else ""

            if command == "help":
                handle_help()
            elif command == "exit":
                handle_exit()
            elif command == "add":
                # Removed 'add food from search' as it's handled in the pager
                if args.lower().startswith("food"):
                    # Pass the rest of the args after "food"
                    handle_add_food(app_data, args[len("food"):].strip())
                elif args.lower().startswith("meal"):
                     handle_add_meal(app_data, args[len("meal"):].strip())
                elif args.lower().startswith("activity"):
                     handle_add_activity(app_data, args[len("activity"):].strip())
                else:
                    console.print(f"[yellow]Unknown 'add' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "list":
                if args.lower().startswith("foods"): # Use startswith to allow for arguments
                    # Pass the rest of the args after "foods" as the filter pattern
                    handle_list_foods(app_data, args[len("foods"):].strip())
                elif args.lower() == "meals":
                     handle_list_meals(app_data)
                elif args.lower().startswith("activities"): # Use startswith to allow for arguments
                     handle_list_activities(app_data, args[len("activities"):].strip())
                else:
                     console.print(f"[yellow]Unknown 'list' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "delete":
                if args.lower().startswith("food"):
                     # Pass the rest of the args after "food"
                    handle_delete_food(app_data, args[len("food"):].strip())
                elif args.lower().startswith("meal"):
                     handle_delete_meal(app_data, args[len("meal"):].strip())
                elif args.lower().startswith("activity"):
                     handle_delete_activity(app_data, args[len("activity"):].strip())
                else:
                    console.print(f"[yellow]Unknown 'delete' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "search":
                 if args.lower().startswith("food"):
                     # Pass the rest of the args after "food" as the search query
                     # Pass app_data but NOT the main_session to handle_search_food
                     handle_search_food(app_data, args[len("food"):].strip())
                     # The pager's session handles its own prompt and exits its loop.
                     # The main loop's session.prompt() will be called again automatically here.
                 else:
                     console.print(f"[yellow]Unknown 'search' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "edit":
                 if args.lower().startswith("meal"):
                      handle_edit_meal(app_data, args[len("meal"):].strip())
                 elif args.lower().startswith("activity"):
                      handle_edit_activity(app_data, args[len("activity"):].strip())
                 else:
                      console.print(f"[yellow]Unknown 'edit' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            # --- Daily Diary Commands ---
            elif command == "log":
                 if args.lower().startswith("food"):
                     handle_log_food(app_data)
                 elif args.lower().startswith("meal"):
                     handle_log_meal(app_data)
                 elif args.lower().startswith("activity"):
                     handle_log_activity(app_data)
                 else:
                      console.print(f"[yellow]Unknown 'log' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "view":
                 if args.lower().startswith("day"):
                      handle_view_day(app_data, args[len("day"):].strip())
                 else:
                      console.print(f"[yellow]Unknown 'view' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "remove":
                 if args.lower().startswith("log"):
                      handle_remove_log(app_data, args[len("log"):].strip())
                 else:
                      console.print(f"[yellow]Unknown 'remove' subcommand:[/yellow] {args.split()[0] if args else ''}. Type '[green]help[/green]' for a list of commands.")
            elif command == "summary":
                 handle_summary(app_data, args)
            else:
                console.print(f"[yellow]Unknown command:[/yellow] {command}. Type '[green]help[/green]' for a list of commands.")

        except EOFError:
            # Handle Ctrl+D
            console.print("\n[bold blue]Exiting on EOF.[/bold blue]")
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C
            console.print("\n[bold blue]Exiting on KeyboardInterrupt.[/bold blue]")
            break
        except Exception as e:
            console.print(f"[red]An unexpected error occurred:[/red] {e}")
            # Optionally print traceback for debugging:
            # import traceback
            # console.print(traceback.format_exc())


# --- Entry Point ---

if __name__ == "__main__":
    run_tracker()
