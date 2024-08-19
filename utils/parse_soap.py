def parse_soap_note(text):  
    sections = ["subjective", "objective", "assessment", "plan"]  
    parsed_data = {}  
      
    for section in sections:  
        start_marker = f"**{section.capitalize()}:**"  
        end_marker = f"**{sections[sections.index(section) + 1].capitalize()}:**" if section != "plan" else None  
          
        start_index = text.find(start_marker)  
        if start_index == -1:  
            return {"error": f"Missing section: {section.capitalize()}"}  
          
        start_index += len(start_marker)  
        end_index = text.find(end_marker) if end_marker else len(text)  
          
        parsed_data[section] = text[start_index:end_index].strip()  
      
    return parsed_data