# -*- coding: utf-8 -*-
# # Script: CreateRingCircleCommand.py
# Description: Creates a Rhino command to draw circles based on international ring sizes.
# Author: Peter Bond
# Date: 7 June 2025

import rhinoscriptsyntax as rs
import Eto.Forms as forms
import Eto.Drawing as drawing
import sys
import re # Added for natural sorting
from fractions import Fraction # Added for parsing fractions
import os

# --- Import ring data ---
ring_data_by_country = None
# print("DEBUG ringSizeGenerator: Script started. 'ring_data_by_country' is initially None.")
try:
    # This assumes 'CreateRingCircleCommand.py' (this script) is in a directory (e.g., '.../rhinoPython/'),
    # and 'ringSizes' is a subdirectory within that same directory, containing 'ring_sizes.py'
    # and an '__init__.py' file.
    # Example structure:
    # .../rhinoPython/
    #   ringSizeGenerator.py  (this script, assuming it's in ringSizes folder)
    #   ringSizes/
    #     __init__.py
    #     ring_sizes.py
    #
    # Rhino usually adds the script's directory to sys.path, so direct import should work.
    # Corrected import assuming '.../rhinoPython/' is on sys.path
    # and 'ringSizes' is a package within it.
    # print("DEBUG ringSizeGenerator: Attempting to import ring_data_by_country from ringSizes.ring_sizes")
    from ring_sizes import ring_data_by_country
    # print("DEBUG ringSizeGenerator: Import successful.")
    # print("DEBUG ringSizeGenerator: type(ring_data_by_country) AFTER import statement =", type(ring_data_by_country))
    # if isinstance(ring_data_by_country, dict):
        # print("DEBUG ringSizeGenerator: ring_data_by_country.keys() (first 5 if dict) =", list(ring_data_by_country.keys())[:5])
    # else:
        # print("DEBUG ringSizeGenerator: ring_data_by_country is NOT a dict or is None AFTER import statement.")

except ImportError as e:
    error_message = (
        "Fatal Error: Could not import ring size data.\n{}\n\n"
        "Please ensure:\n"
        "1. The 'ringSizes' package (directory) is in a path discoverable by Python (e.g., alongside this script or in a directory on sys.path).\n"
        "2. The 'ringSizes' package contains 'ring_sizes.py' and an '__init__.py' file.\n"
        "Example structure: .../rhinoPython/ringSizes/ring_sizes.py and .../rhinoPython/ringSizes/__init__.py\n"
        "Current sys.path includes: {}\n"
        "This command cannot run without the data.".format(e, sys.path)
    )
    print("DEBUG ringSizeGenerator: ImportError caught - " + error_message)
    rs.MessageBox(error_message, buttons=0, title="Import Error - Ring Sizes")
    raise # Stop script execution

# print("DEBUG ringSizeGenerator: AFTER import try-except block.")
# print("DEBUG ringSizeGenerator: Current type(ring_data_by_country) before 'if not' check =", type(ring_data_by_country))
# if ring_data_by_country is None:
    # print("DEBUG ringSizeGenerator: ring_data_by_country IS None before 'if not' check.")

if not ring_data_by_country:
    message = "Ring size data (ring_data_by_country) is None or empty after import attempt. Cannot proceed."
    # print("DEBUG ringSizeGenerator: VALIDATION FAILED - " + message)
    rs.MessageBox(message, title="Data Error")
    raise ValueError(message) # Stop script execution
# else:
    # print("DEBUG ringSizeGenerator: VALIDATION PASSED - 'ring_data_by_country' is considered valid.")


# Global variable to hold the dialog instance
# This helps prevent opening multiple dialogs if the command is run again
DIALOG_INSTANCE = None

# --- Helper functions for custom sorting ---
def to_numeric_if_possible(s):
    """
    Attempts to convert a string to a float, handling integers, decimals,
    and common fraction formats (e.g., "1/2", "1+1/4", "1⁄2", "1+1⁄2").
    Returns the float if successful, otherwise the original string.
    """
    if not isinstance(s, str):
        return s # Should not happen if keys are strings

    # Normalize unicode fraction slash to ASCII slash
    s_normalized = s.replace('⁄', '/') # FRACTION SLASH (U+2044)
    s_normalized = s_normalized.replace('½', '1/2').replace('¼', '1/4').replace('¾', '3/4') # Common single char fractions
    # Add more single char unicode fractions if needed: ⅓, ⅔, ⅕, etc.

    try:
        return float(s_normalized)
    except ValueError:
        pass

    # Try to parse mixed numbers like "X+Y/Z"
    mixed_match = re.match(r'^\s*(\d+)\s*\+\s*(\d+)\s*/\s*(\d+)\s*$', s_normalized)
    if mixed_match:
        try:
            whole = int(mixed_match.group(1))
            num = int(mixed_match.group(2))
            den = int(mixed_match.group(3))
            if den == 0: return s # Avoid division by zero
            return float(whole + Fraction(num, den))
        except ValueError:
            return s # Problem with parsing parts

    # Try to parse simple fractions like "Y/Z"
    simple_fraction_match = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', s_normalized)
    if simple_fraction_match:
        try:
            num = int(simple_fraction_match.group(1))
            den = int(simple_fraction_match.group(2))
            if den == 0: return s # Avoid division by zero
            return float(Fraction(num, den))
        except ValueError:
            return s # Problem with parsing parts
            
    return s # Return original string if no conversion worked

def custom_ring_sort_key(size_str):
    """
    Custom sort key for ring sizes.
    Numbers (including fractions) are sorted numerically.
    Strings are sorted naturally (e.g., "Z1" before "Z10").
    Numbers will come before strings.
    """
    numeric_val = to_numeric_if_possible(size_str)
    if isinstance(numeric_val, float):
        return (0, numeric_val)  # Type 0 for numbers
    else:
        # Natural sort for strings: split into text and number parts
        parts = [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(size_str)) if part]
        return (1, parts) # Type 1 for strings/alphanumeric

class RingCircleDialog(forms.Form):
    def __init__(self): # MODIFIED: No arguments initially
        # print("DEBUG RingCircleDialog.__init__: Entered constructor.")
        super(RingCircleDialog, self).__init__() # Explicitly call the base class constructozzr

        # Initialize ring_data as an empty dict or None, to be set later
        self.ring_data = {}
        # print("DEBUG RingCircleDialog.__init__: type(data) received =", type(data)) # Original data handling
        # self.ring_data = data

        self.Title = "Ring Size Generator"
        self.Padding = drawing.Padding(10)
        self.Resizable = False
        # self.ClientSize = drawing.Size(380, 220) # Optional: Adjust for optimal layout

        # Controls
        self.country_label = forms.Label(Text="Select Country/Region:")
        self.country_full_name_label = forms.Label(Text="(select country)") # New label for full name
        self.country_dropdown = forms.DropDown()
        self.country_dropdown.SelectedIndexChanged += self.on_country_selected

        self.size_label = forms.Label(Text="Select Ring Size:")
        self.size_dropdown = forms.DropDown()
        self.size_dropdown.SelectedIndexChanged += self.on_size_selected # Event handler for size changes

        self.accept_button = forms.Button(Text="Generate")
        self.accept_button.Click += self.on_accept_clicked

        self.close_button = forms.Button(Text="Close")
        self.close_button.Click += self.on_close_clicked

        self.diameter_label = forms.Label(Text="Diameter: (select size)") # New label for diameter
        # Defer population until data is set
        # self.country_dropdown.DataStore = sorted(self.ring_data.keys()) # Original population
        # if self.country_dropdown.DataStore:
        #     self.country_dropdown.SelectedIndex = 0
        # self.update_size_dropdown()
        self.country_dropdown.Enabled = False # Disable until data is loaded
        self.size_dropdown.Enabled = False    # Disable until data is loaded

        # Layout
        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(5, 10) # Horizontal, Vertical spacing
        layout.Padding = drawing.Padding(5)
        # print("DEBUG RingCircleDialog.__init__: Layout created. About to add country_label.")
        # print("DEBUG: type of forms.Label is {}, type of self.country_label is {}".format(type(forms.Label), type(self.country_label)))
        
        layout.AddRow(self.country_label)
        layout.AddRow(self.country_dropdown)
        layout.AddRow(self.country_full_name_label) # Add the new label to the layout
        layout.AddRow(self.size_label)
        layout.AddRow(self.size_dropdown)
        layout.AddRow(self.diameter_label) # Add the diameter label to the layout
        layout.AddRow(None) # Spacer

        buttons_layout = forms.DynamicLayout()
        buttons_layout.Spacing = drawing.Size(5,5)
        buttons_layout.AddRow(None, self.accept_button, self.close_button, None) # Center buttons
        layout.AddRow(buttons_layout)
        # print("DEBUG RingCircleDialog.__init__: All rows added to layout. Setting Content.")

        self.Content = layout

    def load_data_and_populate(self, data_to_load):
        """Loads the ring data and populates the dropdowns."""
        # print("DEBUG RingCircleDialog.load_data_and_populate: Called.")
        # print("DEBUG RingCircleDialog.load_data_and_populate: type(data_to_load) =", type(data_to_load))
        self.ring_data = data_to_load

        if self.ring_data and isinstance(self.ring_data, dict): # Ensure ring_data is a usable dict
            self.country_dropdown.DataStore = sorted(self.ring_data.keys())

            default_country_code = 'UK'
            if default_country_code in self.country_dropdown.DataStore:
                self.country_dropdown.SelectedValue = default_country_code
            elif self.country_dropdown.DataStore: # If UK not found, select first if available
                self.country_dropdown.SelectedIndex = 0
            # else: DataStore is empty, dropdown remains disabled

            if self.country_dropdown.DataStore: # Enable if there's anything to select
                self.country_dropdown.Enabled = True
            else: # No countries loaded
                self.country_dropdown.Enabled = False
        else: # ring_data is not valid
            self.country_dropdown.DataStore = []
            self.country_dropdown.Enabled = False

        self.update_country_full_name_label() # Update full name based on initial/default selection
        self.update_size_dropdown() # This will handle enabling/disabling size_dropdown

    def update_country_full_name_label(self):
        """Updates the full name label based on the selected country."""
        # Check if the dropdown is usable and has a selection
        if not self.country_dropdown.Enabled or self.country_dropdown.SelectedIndex < 0 or not self.country_dropdown.SelectedValue:
            self.country_full_name_label.Text = "Full Name: (select country)"
            return

        selected_country_code = self.country_dropdown.SelectedValue
        if selected_country_code and selected_country_code in self.ring_data:
            # Retrieve country data and full name
            country_data = self.ring_data[selected_country_code]
            full_name = country_data.get('full_name', 'N/A')
            self.country_full_name_label.Text = full_name if full_name else "Full Name: (data not found)"
            
    def update_size_dropdown(self):
        # This method populates the ring size dropdown based on the selected country.
        # It will also trigger an update of the diameter label.
        
        if not self.country_dropdown.Enabled or self.country_dropdown.SelectedIndex < 0 or not self.country_dropdown.SelectedValue:
            self.size_dropdown.DataStore = []
            self.size_dropdown.Enabled = False
            self.update_diameter_label() # Update diameter label (will show placeholder)
            return

        selected_country_code = self.country_dropdown.SelectedValue
        if selected_country_code and selected_country_code in self.ring_data:
            country_data = self.ring_data[selected_country_code]
            sizes = country_data.get('sizes', {})
            
            # Use custom sorting for ring sizes
            size_keys = sorted(list(sizes.keys()), key=custom_ring_sort_key)
            
            # The DataStore is populated with the original size keys (strings).
            # If these keys in ring_sizes.py use UTF-8 representations for fractions, they will be displayed as such.
            self.size_dropdown.DataStore = size_keys
            if size_keys:
                self.size_dropdown.SelectedIndex = 0
                self.size_dropdown.Enabled = True
            else:
                self.size_dropdown.DataStore = []
                self.size_dropdown.Enabled = False
        else:
            self.size_dropdown.DataStore = []
            self.size_dropdown.Enabled = False
        
        self.update_diameter_label() # Update diameter after size dropdown is repopulated

    def update_diameter_label(self):
        """Updates the diameter label based on the selected country and size."""
        if not self.size_dropdown.Enabled or self.size_dropdown.SelectedIndex < 0 or not self.size_dropdown.SelectedValue:
            self.diameter_label.Text = "Diameter: (select size)"
            return

        selected_country_code = self.country_dropdown.SelectedValue
        selected_size_key = self.size_dropdown.SelectedValue

        if selected_country_code and selected_size_key and \
           selected_country_code in self.ring_data and \
           'sizes' in self.ring_data[selected_country_code] and \
           selected_size_key in self.ring_data[selected_country_code]['sizes']:
            
            diameter = self.ring_data[selected_country_code]['sizes'][selected_size_key]
            self.diameter_label.Text = "Diameter: {} mm".format(diameter) # Using .format() for robustness
        else:
            self.diameter_label.Text = "Diameter: (N/A)"

    def on_country_selected(self, sender, e):
        self.update_size_dropdown()
        # Ensure the full country name label is also updated when the country selection changes.
        self.update_country_full_name_label() # Update the full name when country changes

    def on_size_selected(self, sender, e):
        """Handles the event when a new ring size is selected from its dropdown."""
        self.update_diameter_label()

    def on_accept_clicked(self, sender, e):
        if self.country_dropdown.SelectedIndex < 0 or not self.country_dropdown.SelectedValue:
            rs.MessageBox("Please select a country/region.", title="Selection Missing")
            return
        if self.size_dropdown.SelectedIndex < 0 or not self.size_dropdown.SelectedValue:
            rs.MessageBox("Please select a ring size.", title="Selection Missing")
            return

        selected_country_code = self.country_dropdown.SelectedValue
        selected_size_key = self.size_dropdown.SelectedValue

        try:
            country_data = self.ring_data[selected_country_code]
            diameter = country_data['sizes'][selected_size_key]
        except KeyError:
            rs.MessageBox("Could not find size data for the current selection.", title="Data Error")
            return
        except Exception as ex:
            rs.MessageBox("An error occurred while retrieving size data: {}".format(ex), title="Error")
            return

        cplane = rs.ViewCPlane() # Gets the CPlane of the active view
        if not cplane:
            rs.MessageBox("Could not get the current construction plane.", title="Rhino Error")
            return

        radius = float(diameter) / 2.0

        # Add circle to Rhino, on the CPlane, centered at CPlane origin
        circle_id = rs.AddCircle(cplane, radius)

        if circle_id:
            print("Created circle for {} size '{}' (Diameter: {}mm, Radius: {}mm) at CPlane origin.".format(
                selected_country_code, selected_size_key, diameter, radius))
            rs.Redraw()
        else:
            rs.MessageBox("Failed to create the circle in Rhino.", title="Rhino Error")

    def on_close_clicked(self, sender, e):
        self.Close()

    def OnClosed(self, e):
        super(RingCircleDialog, self).OnClosed(e)
        global DIALOG_INSTANCE
        if DIALOG_INSTANCE is self:
            DIALOG_INSTANCE = None
        print("Ring Circle Dialog closed.")

def ShowRingsizeGeneratorCmd():
    global DIALOG_INSTANCE
    # print("DEBUG ShowRingCircleDialogCommand: Entered function.")

    # The bare_test_form block was for debugging and can be removed for cleaner code.

    if DIALOG_INSTANCE is None or DIALOG_INSTANCE.IsDisposed:
        # Dialog does not exist or was closed, create a new one
        # print("DEBUG ShowRingCircleDialogCommand: About to instantiate RingCircleDialog.")
        # print("DEBUG ShowRingCircleDialogCommand: Type of ring_data_by_country being passed to constructor:", type(ring_data_by_country)) # Old log
        DIALOG_INSTANCE = RingCircleDialog() # MODIFIED: Instantiate with no arguments
        # print("DEBUG ShowRingCircleDialogCommand: RingCircleDialog() instantiated. Now loading data.")
        DIALOG_INSTANCE.load_data_and_populate(ring_data_by_country) # Set data via method
        # print("DEBUG ShowRingCircleDialogCommand: Data loaded into dialog.")
        # print("DEBUG ShowRingCircleDialogCommand: RingCircleDialog instantiation attempted/completed.")
        
        # Attempt to set owner, but proceed if RhinoApp is not available
        try:
            DIALOG_INSTANCE.Owner = rs.RhinoApp.MainWindow
            # print("DEBUG ShowRingCircleDialogCommand: Dialog owner set to Rhino main window.")
        except AttributeError:
            pass
            # print("DEBUG ShowRingGeneratorCmd: rs.RhinoApp not available. Dialog will not be parented to main window.")
        DIALOG_INSTANCE.Show() # Modeless display
    else:
        # Dialog instance already exists, bring it to the front and ensure it's visible.
        # print("DEBUG ShowRingCircleDialogCommand: Dialog instance already exists, bringing to front.")
        DIALOG_INSTANCE.BringToFront()
        DIALOG_INSTANCE.Show() # Ensures the dialog is visible if it was hidden

def create_or_update_alias():
    """
    Programmatically creates or updates the 'ShowRingsizeGenerator' alias in Rhino
    to point to the current script.
    """
    alias_name = "ShowRingsizeGenerator"
    try:
        # Get the absolute path of the currently running script
        script_path = os.path.abspath(__file__)
        expected_macro = '_-RunPythonScript "{}"'.format(script_path)

        current_macro = rs.AliasMacro(alias_name)

        if current_macro != expected_macro:
            if rs.AddAlias(alias_name, expected_macro):
                print("Rhino alias '{}' created/updated successfully to run this script.".format(alias_name))
            else:
                print("Error: Failed to create/update Rhino alias '{}'.".format(alias_name))
        # else:
            # print("Rhino alias '{}' is already correctly configured.".format(alias_name)) # Optional: for verbose feedback
    except Exception as e:
        print("Error during alias setup for '{}': {}".format(alias_name, e))

if __name__ == "__main__":
    # This block executes when the script is run in Rhino.
    create_or_update_alias() # Ensure the alias is set up

    try:
        ShowRingsizeGeneratorCmd()
        # print("DEBUG ringSizeGenerator: ShowRingCircleDialogCommand() called successfully from __main__.")
    except Exception as e_main:
        print("DEBUG ringSizeGenerator: EXCEPTION in `if __name__ == \"__main__\"`: {}".format(e_main))
        rs.MessageBox("An error occurred running the command: {}".format(e_main), title="Command Error")
        raise # Re-raise to see full traceback if possible
