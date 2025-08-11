export function PopularEntries({ darkMode = false }) {
  const entries = [
    {
      query: "What are the names of properties that are either houses or apartments with more than 5 room?",
      uses: 17,
    },
    {
      query: "What are the names of properties that are either houses or apartments with more than 1 room?",
      uses: 4,
    },
    {
      query: "What are the birth year and citizenship of singers?",
      uses: 1,
    },
    {
      query: "What are the citizenships that are shared by singers with a birth year before 1945 and after 1955?",
      uses: 1,
    },
    {
      query: "Where the names, friends, and ages of all people who are older than the average age of a person?",
      uses: 0,
    },
  ]

  return (
    <div className="space-y-4">
      {entries.map((entry, index) => (
        <div key={index} className="flex items-start justify-between gap-4 py-2">
          <div className={`text-sm line-clamp-2 ${darkMode ? "text-white" : ""}`}>{entry.query}</div>
          <div className={`text-xs whitespace-nowrap ${darkMode ? "text-slate-400" : "text-muted-foreground"}`}>
            {entry.uses} {entry.uses === 1 ? "use" : "uses"}
          </div>
        </div>
      ))}
    </div>
  )
}
