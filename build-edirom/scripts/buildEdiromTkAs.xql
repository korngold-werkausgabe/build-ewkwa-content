xquery version "3.1";

declare namespace edirom = "http://www.edirom.de/ns/1.3";
declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace transform = "http://exist-db.org/xquery/transform";
declare namespace xmldb = "http://exist-db.org/xquery/xmldb";
declare namespace array = "http://www.w3.org/2005/xpath-functions/array";
declare namespace util = "http://exist-db.org/xquery/util";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";
declare namespace math = "http://www.w3.org/2005/xpath-functions/math";

declare variable $cnList as xs:string? external := "";
declare variable $cnListFile as xs:string? external := "";
declare variable $collectionPath as xs:string external;
declare variable $sourcesPath as xs:string external;
declare variable $subDiv as xs:string external;
declare variable $volumeName as xs:string external;

declare function local:composePath($volume as xs:string, $subDiv as xs:string?, $rest as xs:string) as xs:string {
  let $subDivPath :=
    if ($subDiv and $subDiv != "" and $subDiv != "None" and $subDiv != $volume)
    then "/" || $subDiv
    else ""
  return "xmldb:exist:///db/apps/edirom-content/" || $volume || $subDivPath || "/" || $rest
};

declare function local:sourceFileName($doc as node()?) as xs:string {
  if (empty($doc)) then ''
  else
    let $root := if ($doc instance of document-node()) then $doc else root($doc)
    let $base := string((base-uri($root), document-uri($root), base-uri($doc), document-uri($doc))[1])
    let $file-name := tokenize($base, '/')[last()]
    return if (string-length($file-name) gt 0) then $file-name else ''
};

declare function local:measureIdsToUris($sourceDoc as node()?, $measure-ids as xs:string*, $subDiv as xs:string*) as xs:string* {
  let $base := local:sourceFileName($sourceDoc)
  let $url := local:composePath($volumeName, $subDiv, 'sources/')
  return
    if ($base != '' and exists($measure-ids)) then
      for $id in distinct-values($measure-ids[string-length(normalize-space(.)) gt 0])
      return concat($url, $base, '#', normalize-space($id))
    else
      ()
};

declare function local:measureLabel($measure as node()) as xs:string {
  if (empty($measure)) then ''
  else if (local-name($measure) = 'sequence') then
    let $from := string(($measure/@label-from, $measure/@label, $measure/@n)[1])
    let $to := string(($measure/@label-to, $measure/@label, $measure/@n)[last()])
    return if ($from != '' and $to != '') then concat($from, '–', $to) else ($from, $to)[1]
  else
    string(($measure/@label, $measure/@n, $measure/@xml:id, $measure/@id)[1])
};

declare function local:measuresToString($measures as node()?) as xs:string {
  let $measures-string := for $node in $measures/*
  return
    switch ($node/name())
      case 'measure'
        return concat(local:measureLabel($node), ' ')
      case 'sequence'
        return concat(local:measureLabel($node), ' ')
      default
        return
          ''
  return
    concat('T. ', string-join($measures-string, ', '))
};

declare function local:pitchToString($pitch as node()*) as xs:string {
  let $pname := if (xs:int($pitch/@oct/normalize-space()) <= 2)
  then
    upper-case($pitch/@pname/normalize-space())
  else
    $pitch/@pname/normalize-space()
  let $oct := if (xs:int($pitch/@oct/normalize-space()) >= 4)
  then
    xs:int($pitch/@oct/normalize-space()) - 3
  else
    if (xs:int($pitch/@oct/normalize-space()) >= 2)
    then
      ()
    else
      if (xs:int($pitch/@oct/normalize-space()) = 1)
      then
        1
      else
        0
  return
    concat($pname, if ($oct) then concat('', $oct) else '')
};

declare function local:buildChord($chord as node()*) as xs:string {
  string-join(
    for $pitch in $chord/pitch
    return
      local:pitchToString($pitch),
    '/'
  )
};

declare function local:buildSequence($sequence as node()*) as xs:string {
  string-join(
    for $pitch in $sequence/pitch
    return
      local:pitchToString($pitch),
    '–'
  )
};

declare function local:buildSmufl($symbol as node()) as item()* {
  let $glyph-uri := concat('https://smufl.korngold-werkausgabe.de/', $symbol/@glyph.name, '.xml')
  return
    <rend xmlns="http://www.music-encoding.org/ns/mei" glyph.uri="{$glyph-uri}"/>
};

declare function local:renderPitchMarkup($pitch as node()) as item()* {
  let $pname := normalize-space(string($pitch/@pname))
  let $octValue := normalize-space(string($pitch/@oct))
  let $octLabel :=
    if ($octValue = '1') then 'Subkontra'
    else if ($octValue = '2') then 'Kontra'
    else ''
  let $noteName := upper-case(substring($pname, 1, 1)) || substring($pname, 2)
  let $octavePart :=
    if ($octValue = '0' or $octValue = '1' or $octValue = '2') then ''
    else if ($octValue != '') then $octValue else ''
  return
    if ($octLabel != '') then
      <rend xmlns="http://www.music-encoding.org/ns/mei" rend="italic">{concat($octLabel, '-', $noteName)}</rend>
    else (
      <rend xmlns="http://www.music-encoding.org/ns/mei" rend="italic">{$noteName}</rend>,
      if ($octavePart != '') then
        <rend xmlns="http://www.music-encoding.org/ns/mei" rend="sup">{$octavePart}</rend>
      else
        ()
    )
};

declare function local:buildNoteTextContent($nodes as node()*, $sources as node()*, $subDiv as xs:string, $volumeName as xs:string, $pos as xs:integer) as item()* {
  for $node at $index in $nodes[position() >= $pos]
  return
    if ($node/self::element()) then
      switch ($node/name())
        case 'measures'
          return local:measuresToString($node)
        case 'siglum'
          return <rend rend="bold">{$node/@siglum/normalize-space()}</rend>
        case 'pitch'
          return local:renderPitchMarkup($node)
        case 'chord'
          return local:buildChord($node)
        case 'pitch-sequence'
          return local:buildSequence($node)
        case 'musicalSymbol'
          return local:buildSmufl($node)
        case 'rend'
          return
            <rend xmlns="http://www.music-encoding.org/ns/mei" rend="{string($node/@rend)}">{
              $node/node()
            }</rend>
        case 'quote'
          return
            <rend xmlns="http://www.music-encoding.org/ns/mei" rend="it">[{string-join(for $text in $node//text() return normalize-space($text), ' ')}]</rend>
        default
          return ''
    else
      $node/string()
};

declare function local:expandMeasureSequenceValue($value as xs:string?) as xs:string* {
  let $normalized := normalize-space(string($value))
  return
    if ($normalized = '') then ()
    else if (matches($normalized, '^\d+\s*(?:[-–]\s*\d+)+$')) then
      let $parts := tokenize(replace($normalized, '–', '-'), '-')
      let $from := xs:integer(normalize-space($parts[1]))
      let $to := xs:integer(normalize-space($parts[last()]))
      return
        if ($from <= $to) then
          for $i in $from to $to return xs:string($i)
        else
          for $i in $to to $from return xs:string($i)
    else
      $normalized
};

declare function local:convertToMeasuresElement($measure-string as xs:string*, $siglum as xs:string*, $mdiv as xs:string*) as node()* {
  let $items :=
    for $token in tokenize(string-join($measure-string, ','), ',')
    let $item := normalize-space($token)
    return if ($item != '') then $item else ()
  return
    <measures>
      {
        for $item in $items
        return
          if (matches($item, '^\d+\s*(?:[-–]\s*\d+)+$')) then
            let $parts := tokenize(replace($item, '–', '-'), '-')
            let $from := normalize-space($parts[1])
            let $to := normalize-space($parts[last()])
            return
              <sequence
                source="{$siglum}"
                siglum="{$siglum}"
                label-from="{$from}"
                label-to="{$to}"
                mdiv="{$mdiv}"/>
          else
            <measure
              source="{$siglum}"
              siglum="{$siglum}"
              mdiv="{$mdiv}"
              label="{$item}"/>
      }
    </measures>
};

declare function local:resolveIdRef($value as xs:string?) as xs:string {
  let $normalized := normalize-space(string($value))
  return
    if ($normalized = '') then ''
    else if (contains($normalized, '#')) then
      normalize-space(substring-after($normalized, '#'))
    else
      $normalized
};

declare function local:cnListSourceId($cnList as node()?) as xs:string {
  if (empty($cnList)) then ''
  else local:resolveIdRef(string(($cnList/@main-source, $cnList/@source-target, $cnList/@source)[1]))
};

declare function local:cnListMdivId($cnList as node()?) as xs:string {
  if (empty($cnList)) then ''
  else local:resolveIdRef(string(($cnList/@mdiv-target, $cnList/@mdiv, $cnList/@target)[1]))
};

declare function local:sourceDocForCnList($sources as node()*, $cnList as node()?, $measure as node()?) as document-node()? {
  let $source-id :=
    if (exists($cnList)) then local:cnListSourceId($cnList)
    else if (exists($measure)) then local:resolveIdRef(string(($measure/@source, $measure/@main-source, $measure/@source-target, $measure/@siglum)[1]))
    else ''
  let $source-node :=
    if ($source-id = '') then ()
    else ($sources//*[@xml:id = $source-id or @id = $source-id][1])
  return
    if (empty($source-node)) then ()
    else root($source-node)
};

declare function local:measureRefValues($measure as node()) as xs:string* {
  let $values := (
    string($measure/@label),
    string($measure/@n),
    string($measure/@xml:id),
    string($measure/@id),
    if (local-name($measure) = 'sequence') then (
      let $from := string(($measure/@label-from, $measure/@label, $measure/@n)[1])
      let $to := string(($measure/@label-to, $measure/@label, $measure/@n)[last()])
      return
        if ($from != '' and $to != '' and matches($from, '^\d+$') and matches($to, '^\d+$')) then
          for $i in xs:integer($from) to xs:integer($to)
          return xs:string($i)
        else (
          $from,
          $to
        )
    ) else (),
    if (local-name($measure) = 'measure' and matches(normalize-space(string($measure/@label)), '^\d+\s*(?:[-–]\s*\d+)+$')) then
      local:expandMeasureSequenceValue(string($measure/@label))
    else ()
  )
  return distinct-values($values[string-length(normalize-space(.)) gt 0])
};

declare function local:findMeasureInSource($sourceDoc as node()*, $mdiv-target-id as xs:string?, $measure-label as xs:string?, $siglum as xs:string?) as element()? {
  let $mdivMatches :=
    if ($sourceDoc and $mdiv-target-id != '') then
      $sourceDoc//mei:mdiv[@xml:id = $mdiv-target-id or @id = $mdiv-target-id or @n = $mdiv-target-id]
    else
      ()
  let $labelMatches := (
    if (exists($mdivMatches)) then (
      $mdivMatches//mei:measure[
        ($siglum = '' or @siglum = $siglum or @siglum = '' or not(@siglum))
        and (
          @label = $measure-label or @n = $measure-label or @xml:id = $measure-label or @id = $measure-label
        )
      ]
    ) else (),
    if ($siglum != '') then (
      $sourceDoc//mei:measure[
        @siglum = $siglum
        and (
          @label = $measure-label or @n = $measure-label or @xml:id = $measure-label or @id = $measure-label
        )
      ]
    ) else (),
    if ($measure-label != '') then (
      $sourceDoc//mei:measure[
        @label = $measure-label or @n = $measure-label or @xml:id = $measure-label or @id = $measure-label
      ]
    ) else ()
  )
  return
    if (exists($labelMatches)) then $labelMatches[1] else ()
};

declare function local:resolveMeasureUris($sources as node()*, $measure as node()*, $subDiv as xs:string*) as xs:string* {
  let $cnList := ($measure/ancestor::*[@main-source or @source-target][1], $measure/parent::*[@main-source or @source-target])[1]
  let $sourceDoc := local:sourceDocForCnList($sources, $cnList, $measure)
  let $mdiv-target-id := if (exists($cnList)) then local:cnListMdivId($cnList) else local:resolveIdRef(string(($measure/@mdiv, $measure/@part, $measure/@staff)[1]))
  let $measure-ids := distinct-values(
    for $measure-label in local:measureRefValues($measure)
    let $match := local:findMeasureInSource($sourceDoc, $mdiv-target-id, $measure-label, string($measure/@siglum))
    return if (exists($match)) then string($match/@xml:id) else ()
  )
  return
    if (count($measure-ids) gt 0) then
      local:measureIdsToUris($sourceDoc, $measure-ids, $subDiv)
    else if (empty($sourceDoc) or empty($cnList)) then
      ()
    else
      let $measure-xml-id := string(($measure/@xml:id, $measure/@id)[1])
      let $measure-n := string(($measure/@n, $measure/@label)[1])
      let $measure-label := string(($measure/@label, $measure/@n)[1])
      let $mdiv-name := xs:string(($measure/@mdiv, $measure/@part, $measure/@staff)[1])
      let $siglum := xs:string(($measure/@siglum)[1])
      let $fallbackMatch := (
        $sourceDoc//mei:measure[@xml:id = $measure-xml-id],
        $sourceDoc//mei:measure[@id = $measure-xml-id],
        $sourceDoc//mei:measure[@n = $measure-n],
        $sourceDoc//mei:measure[@label = $measure-label],
        $sourceDoc//mei:mdiv[@xml:id = $mdiv-name or @id = $mdiv-name or @n = $mdiv-name]//mei:measure[@xml:id = $measure-xml-id or @id = $measure-xml-id or @n = $measure-n or @label = $measure-label]
      )[1]
      let $fallback-id := if (exists($fallbackMatch)) then xs:string($fallbackMatch/@xml:id) else ()
      return if ($fallback-id != '') then local:measureIdsToUris($sourceDoc, $fallback-id, $subDiv) else ()
};

declare function local:noteMeasureUri($sources as node()*, $note as node(), $subDiv as xs:string*) as xs:string* {
  let $cnList := ($note/ancestor::*[@main-source or @source-target][1], $note/parent::*[@main-source or @source-target])[1]
  let $sourceDoc := local:sourceDocForCnList($sources, $cnList, ())
  let $mdiv-target-id := local:cnListMdivId($cnList)
  let $measureNodes := (
    $note/*:measures/*[self::mei:measure or self::mei:sequence],
    $note/*:measures/*:measure,
    $note/*:noteText//*[local-name() = 'measure' or local-name() = 'sequence']
  )
  return
    for $measure in $measureNodes
    let $measure-labels := local:measureRefValues($measure)
    for $measure-label in $measure-labels
    let $match := local:findMeasureInSource($sourceDoc, $mdiv-target-id, $measure-label, string($measure/@siglum))
    let $measure-id := if (exists($match)) then string($match/@xml:id) else ()
    return
      if ($sourceDoc and $measure-id != '') then
        let $url := local:composePath($volumeName, $subDiv, 'sources/')
        let $base := local:sourceFileName($sourceDoc)
        return concat($url, $base, '#', $measure-id)
      else ()
};

declare function local:measureUri($sources as node()*, $measure as node()*, $subDiv as xs:string*) as xs:string {
  string-join(local:resolveMeasureUris($sources, $measure, $subDiv), ' ')
};

declare function local:noteMeasures($note as node()) as node()* {
  (
    $note/*:measures/*,
    $note/*:noteText//*[local-name() = 'measure' or local-name() = 'sequence']
  )
};

declare function local:measuresStringToElement($sources as node()*, $measures as node(), $subDiv as xs:string*) as xs:string {
  string-join(
    for $sub-node in $measures/*
    return
      switch (local-name($sub-node))
        case 'measure'
          return local:measureUri($sources, $sub-node, $subDiv)
        case 'sequence'
          return (
            let $from := normalize-space(string(($sub-node/@label-from, $sub-node/@label, $sub-node/@n)[1]))
            let $to := normalize-space(string(($sub-node/@label-to, $sub-node/@label, $sub-node/@n)[last()]))
            return
              if ($from != '' and $to != '' and matches($from, '^\d+$') and matches($to, '^\d+$')) then
                string-join(
                  for $i in xs:integer($from) to xs:integer($to)
                  return local:measureUri(
                    $sources,
                    <measure
                      siglum="{$sub-node/@siglum/string()}"
                      mdiv="{$sub-node/@mdiv/string()}"
                      label="{xs:string($i)}"/>,
                    $subDiv
                  ),
                  ' '
                )
              else
                local:measureUri(
                  $sources,
                  <measure
                    siglum="{$sub-node/@siglum/string()}"
                    mdiv="{$sub-node/@mdiv/string()}"
                    label="{$from}"/>,
                  $subDiv
                )
          )
        default
          return ''
    ,
    ' '
  )
};

(: Paths and input documents :)

let $cnListNode :=
  if ($cnListFile != "") then
    doc($cnListFile)
  else
    parse-xml-fragment($cnList)
let $sources := collection($sourcesPath)

let $plist := map:merge(
  for $note in $cnListNode//criticalNote
  let $measures := local:noteMeasures($note)
  let $resolved := (
    for $measure in $measures
    return local:measureUri($sources, $measure, $subDiv),
    local:noteMeasureUri($sources, $note, $subDiv)
  )
  return
    map:entry(
      string($note/@xml:id),
      string-join(
        for $uri in distinct-values($resolved[string-length(normalize-space(.)) gt 0])
        return normalize-space($uri),
        ' '
      )
    )
)

let $criticalNotes :=
  for $note in $cnListNode//*:criticalNote
    let $measureText := normalize-space(string($note/*:measures/text()))
    let $mainSourcePlist := if ($measureText != '') then
      string-join(
        distinct-values(
          (
            local:measuresStringToElement(
              $sources,
              local:convertToMeasuresElement($measureText, local:cnListSourceId($note/ancestor::*[@main-source or @source-target][1]), local:cnListMdivId($note/ancestor::*[@main-source or @source-target][1])),
              $subDiv
            ),
            local:noteMeasureUri($sources, $note, $subDiv)
          )[string-length(normalize-space(.)) gt 0]
        ),
        ' '
      )
    else
      ''
    let $titleText :=
      string-join(
        (
          if ($note/*:measures[normalize-space()]) then concat('T. ', string($note/*:measures/normalize-space())) else (),
          if ($note/*:staff[normalize-space()]) then string($note/*:staff/normalize-space()) else (),
          if ($note/*:musicalEvent[normalize-space()]) then string($note/*:musicalEvent/normalize-space()) else ()
        )[string(.) != ''],
        ' | '
      )
    return
      let $plist-values := distinct-values(
        for $item in (string($mainSourcePlist), string(map:get($plist, $note/@xml:id/string())))
        return if (normalize-space($item) != '') then normalize-space($item) else ()
      )
      return
        <annot
          xmlns="http://www.music-encoding.org/ns/mei"
          xml:id="{$note/@xml:id}"
          type="editorialComment"
          class="#ediromAnnotPrio1 {concat('#', string-join($note/*:categories/@values/data(), ' '))}"
          plist="{string-join($plist-values, ' ')}"
        >
        <title
          lang="de">{$titleText}</title>
        <p>{
            local:buildNoteTextContent($note/*:noteText/node(), $sources, $subDiv, $volumeName, 1)
        }</p>
    </annot>

return
  $criticalNotes