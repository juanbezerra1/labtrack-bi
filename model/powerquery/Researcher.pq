// labtrack-bi: query of the table Researcher (dim_researcher.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Researcher.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\dim_researcher.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Cleaned = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"researcher_key", "full_name", "role", "hired_on", "left_on"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"researcher_key", Int64.Type}, {"full_name", type text}, {"role", type text}, {"hired_on", type date}, {"left_on", type date}}, "en-US"),
    Labelled = Table.TransformColumns(Typed, {{"role", each if _ = null then null else Record.FieldOrDefault([pi = "PI", postdoc = "Postdoc", phd = "PhD", msc = "MSc", technician = "Technician"], _, _), type text}}),
    Renamed = Table.RenameColumns(Labelled, {{"researcher_key", "Researcher Key"}, {"full_name", "Researcher"}, {"role", "Role"}, {"hired_on", "Hired On"}, {"left_on", "Left On"}}),
    Selected = Table.SelectColumns(Renamed, {"Researcher Key", "Researcher", "Role", "Hired On", "Left On"})
in
    Selected
