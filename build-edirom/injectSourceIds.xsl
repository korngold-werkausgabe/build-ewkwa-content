<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:mei="http://www.music-encoding.org/ns/mei"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema"
  exclude-result-prefixes="xs" version="2.0">

  <xsl:output indent="yes"/>
  <xsl:param name="kbSources" select="document('../../Quellenuebersicht/kb_sources.xml')"/>

  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="mei:mei">
    <xsl:variable name="currentSiglum" select=".//mei:identifier[@type = 'siglum']/text()"/>
    <mei xml:id="{$kbSources//*:source[*:siglum[text() = $currentSiglum]]/@xml:id}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()"/>
    </mei>
  </xsl:template>
</xsl:stylesheet>
